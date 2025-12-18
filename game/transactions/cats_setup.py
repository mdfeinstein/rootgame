from django.db import transaction
from game.models.cats.buildings import (
    CatBuildingTypes,
    Recruiter,
    Sawmill,
    Workshop,
)
from game.models.cats.setup import CatsSimpleSetup
from game.models.cats.tokens import CatKeep, CatWood
from game.models import (
    Building,
    BuildingSlot,
    Clearing,
    Game,
    Player,
    Warrior,
    WarriorSupplyEntry,
)
from game.queries.general import available_building_slot
from game.models.events.setup import GameSimpleSetup

from game.queries.setup.cats import (
    validate_building_type,
    validate_keep_is_here_or_adjacent,
    validate_timing,
)
from game.transactions.cats import create_cats_turn
from game.transactions.setup_util import next_player_setup
from game.utility.textchoice import next_choice


@transaction.atomic
def create_cats_warrior_supply(player: Player):
    # create warriors
    warriors = [Warrior(player=player) for _ in range(25)]
    for warrior in warriors:
        warrior.save()
    # assign warriors to supply
    supply_entries = [
        WarriorSupplyEntry(player=player, warrior=warrior) for warrior in warriors
    ]
    WarriorSupplyEntry.objects.bulk_create(supply_entries)


@transaction.atomic
def create_cats_wood_supply(player: Player):
    # create wood tokens
    for i in range(8):
        CatWood(player=player).save()


@transaction.atomic
def create_cats_keep(player: Player):
    # create keep
    CatKeep(player=player, clearing=None).save()


@transaction.atomic
def create_cats_buildings(player: Player):
    # create 5 of each building in player supply (null clearing)
    for i in range(6):
        Workshop(player=player, building_slot=None).save()
        Recruiter(player=player, building_slot=None).save()
        Sawmill(player=player, building_slot=None).save()


@transaction.atomic
def start_simple_cats_setup(player: Player) -> CatsSimpleSetup:
    create_cats_warrior_supply(player)
    create_cats_keep(player)
    create_cats_wood_supply(player)
    create_cats_buildings(player)
    setup = CatsSimpleSetup(player=player, step=CatsSimpleSetup.Steps.PICKING_CORNER)
    setup.save()
    return setup


@transaction.atomic
def pick_corner(player: Player, clearing: Clearing):
    """picks a corner for the keep"""
    # check that it is cats setup
    validate_timing(player, CatsSimpleSetup.Steps.PICKING_CORNER)
    keep = CatKeep.objects.get(player=player)
    keep.clearing = clearing
    keep.save()
    cats_setup = CatsSimpleSetup.objects.get(player=player)
    cats_setup.step = next_choice(CatsSimpleSetup.Steps, cats_setup.step)
    print(cats_setup.step)
    cats_setup.save()


# this is general logic that shoudl be extracted out of setup later
@transaction.atomic
def place_warrior(player: Player, clearing: Clearing):
    # grab a warrior from the supply
    warrior_supply = WarriorSupplyEntry.objects.filter(player=player).first()
    if warrior_supply is None:
        raise ValueError("No warriors left to place")
    # assign clearing to warrior
    warrior_supply.warrior.clearing = clearing
    warrior_supply.warrior.save()
    # remove warrior from supply
    warrior_supply.delete()


@transaction.atomic
def place_building(
    player: Player, building_type: CatBuildingTypes, building_slot: BuildingSlot
):
    """places a building of the given type from the supply in the given clearing
    also applies scoring for the player
    """
    # check that the building_slot is empty
    if Building.objects.filter(building_slot=building_slot).exists():
        raise ValueError("Building slot is not empty")

    scoring_after_placement = (
        {  # idx: [0 on board (before placement), 1 on board,... 6 on board] val: score
            CatBuildingTypes.SAWMILL: [0, 1, 2, 3, 4, 5],
            CatBuildingTypes.WORKSHOP: [0, 2, 2, 3, 4, 5],
            CatBuildingTypes.RECRUITER: [0, 1, 2, 3, 3, 4],
        }
    )
    # place building from supply and score
    if building_type == CatBuildingTypes.WORKSHOP:
        buildings = Workshop.objects.filter(player=player, building_slot=None)
    elif building_type == CatBuildingTypes.SAWMILL:
        buildings = Sawmill.objects.filter(player=player, building_slot=None)
    else:  # recruiter
        buildings = Recruiter.objects.filter(player=player, building_slot=None)

    count_in_supply = buildings.count()
    count_on_board = Building.objects.filter(
        player=player, building_slot__isnull=False
    ).count()
    if count_in_supply == 0:
        raise ValueError("No workshops left to place")
    building = buildings.first()

    assert building is not None  # we should have already raised if so
    # assign building_slot
    building.building_slot = building_slot
    building.save()

    # find and adjust score
    score = scoring_after_placement[building_type][count_on_board]
    player.score += score
    player.save()
    return score


@transaction.atomic
def place_garrison(player: Player, clearing_to_avoid: Clearing):
    """places one warrior everywhere except the clearing_to_avoid"""
    clearings_to_place = list(
        Clearing.objects.filter(game=player.game).exclude(pk=clearing_to_avoid.pk)
    )
    warriors_from_supply = list(
        WarriorSupplyEntry.objects.filter(player=player)[: len(clearings_to_place)]
    )
    for supply_warrior, clearing in zip(warriors_from_supply, clearings_to_place):
        supply_warrior.warrior.clearing = clearing
    # bulk update the warriors (not the supply entries)
    Warrior.objects.bulk_update([s.warrior for s in warriors_from_supply], ["clearing"])
    # bulk delete the supply entries by primary key
    WarriorSupplyEntry.objects.filter(
        pk__in=[s.pk for s in warriors_from_supply]
    ).delete()


@transaction.atomic
def place_initial_building(
    player: Player, clearing: Clearing, building_type: CatBuildingTypes
):
    """places initial buildings for cats: 1 Workshop, 1 Sawmill, 1 Recruiter
    In clearings adjacent to the keep.
    """
    # check that it is cats setup
    validate_timing(player, CatsSimpleSetup.Steps.PLACING_BUILDINGS)

    setup = CatsSimpleSetup.objects.get(player=player)
    # check that building_type has not been placed yet
    validate_building_type(player, building_type)
    # check that the clearing is adjacent to the keep or is the same as the keep
    validate_keep_is_here_or_adjacent(player, clearing)

    building_slot = available_building_slot(clearing)
    if building_slot is None:
        raise ValueError("No free building slots")
    # otherwise place the building
    place_building(player, building_type, building_slot)
    building_slots = BuildingSlot.objects.filter(clearing=clearing)

    # update setup
    placed_field_mapper = {
        CatBuildingTypes.WORKSHOP: "workshop_placed",
        CatBuildingTypes.SAWMILL: "sawmill_placed",
        CatBuildingTypes.RECRUITER: "recruiter_placed",
    }
    setattr(setup, placed_field_mapper[building_type], True)
    # check if all buildings have been placed
    all_placed = all(
        [getattr(setup, placed_field) for placed_field in placed_field_mapper.values()]
    )
    if all_placed:
        setup.step = next_choice(CatsSimpleSetup.Steps, setup.step)
    setup.save()


@transaction.atomic
def confirm_completed_setup(player: Player):
    # check that it is cats setup
    simple_setup = GameSimpleSetup.objects.get(game=player.game)
    if simple_setup.status != GameSimpleSetup.GameSetupStatus.CATS_SETUP:
        raise ValueError("Not this player's setup turn")
    # check that the step is pending confirmation
    setup = CatsSimpleSetup.objects.get(player=player)
    if setup.step != CatsSimpleSetup.Steps.PENDING_CONFIRMATION:
        raise ValueError("Setup not complete")
    setup.step = next_choice(CatsSimpleSetup.Steps, setup.step)
    setup.save()
    next_player_setup(player.game)
    # create first turn
    create_cats_turn(player)
