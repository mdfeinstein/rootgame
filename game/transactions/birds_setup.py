from game.models.birds.buildings import BirdRoost
from game.models.birds.player import BirdLeader
from game.models.birds.setup import BirdsSimpleSetup
from game.models import Clearing, Player, Warrior, WarriorSupplyEntry
from django.db import transaction

from game.db_selectors.general import available_building_slot
from game.models.cats.tokens import CatKeep
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import Faction
from game.utility.textchoice import next_choice


@transaction.atomic
def create_birds_warrior_supply(player: Player):
    # create warriors
    warriors = [Warrior(player=player) for _ in range(20)]
    for warrior in warriors:
        warrior.save()
    # assign warriors to supply
    supply_entries = [
        WarriorSupplyEntry(player=player, warrior=warrior) for warrior in warriors
    ]
    WarriorSupplyEntry.objects.bulk_create(supply_entries)


@transaction.atomic
def create_birds_buildings(player: Player):
    # create 7 roosts
    for i in range(7):
        BirdRoost(player=player, building_slot=None).save()


@transaction.atomic
def create_bird_leaders(player: Player):
    for leader_value, _ in BirdLeader.BirdLeaders.choices:
        BirdLeader(player=player, leader=leader_value).save()


@transaction.atomic
def start_simple_birds_setup(player: Player) -> BirdsSimpleSetup:
    setup = BirdsSimpleSetup(player=player, step=BirdsSimpleSetup.Steps.PICKING_CORNER)
    setup.save()
    create_birds_warrior_supply(player)
    create_birds_buildings(player)
    create_bird_leaders(player)
    return setup


@transaction.atomic
def pick_corner(player: Player, clearing: Clearing):
    "intial roost and warrior placement"
    # external check assumed: not the same clearing as another player
    # check that it is birds setup
    simple_setup = GameSimpleSetup.objects.get(game=player.game)
    if simple_setup.status != GameSimpleSetup.GameSetupStatus.BIRDS_SETUP:
        raise ValueError("Not this player's setup turn")

    birds_setup = BirdsSimpleSetup.objects.get(player=player)
    if birds_setup.step != BirdsSimpleSetup.Steps.PICKING_CORNER:
        raise ValueError("this has been triggered at the wrong step")
    # If cats keep is out, pick roost opposite
    game = player.game
    try:
        cat_player = Player.objects.get(game=game, faction=Faction.CATS)
        keep = CatKeep.objects.get(player=cat_player)
        opposite_clearing_number = ((keep.clearing.clearing_number - 1 + 2) % 4) + 1
        opposite_clearing = Clearing.objects.get(
            game=game, clearing_number=opposite_clearing_number
        )
        if opposite_clearing != clearing:
            raise ValueError("Keep is not in the opposite corner")
    except (Player.DoesNotExist, CatKeep.DoesNotExist):
        pass
    # place roost, assuming a free building slot
    roost = BirdRoost.objects.filter(player=player, building_slot=None).first()
    assert roost is not None, "no available roost found in setup!"
    building_slot = available_building_slot(clearing)
    if building_slot is None:
        raise ValueError("No free building slot")
    roost.building_slot = building_slot
    roost.save()

    # place 6 warriors
    warriors_in_supply = list(WarriorSupplyEntry.objects.filter(player=player)[:6])
    assert len(warriors_in_supply) == 6, "not 6 warriors in supply during setup!"
    # bulk place warriors by assigning clearing and bulk updating the warriors
    for supply_warrior in warriors_in_supply:
        supply_warrior.warrior.clearing = clearing
    Warrior.objects.bulk_update([sw.warrior for sw in warriors_in_supply], ["clearing"])
    # bulk delete the supply entries by primary key
    WarriorSupplyEntry.objects.filter(
        pk__in=[sw.pk for sw in warriors_in_supply]
    ).delete()

    # update setup
    birds_setup.step = BirdsSimpleSetup.Steps.CHOOSING_LEADER
    birds_setup.save()


@transaction.atomic
def choose_leader_initial(player: Player, leader: BirdLeader.BirdLeaders):
    """choose leader and update setup"""
    # check that it is birds setup
    simple_setup = GameSimpleSetup.objects.get(game=player.game)
    if simple_setup.status != GameSimpleSetup.GameSetupStatus.BIRDS_SETUP:
        raise ValueError("Not this player's setup turn")

    bird_setup = BirdsSimpleSetup.objects.get(player=player)
    if bird_setup.step != BirdsSimpleSetup.Steps.CHOOSING_LEADER:
        raise ValueError("this has been triggered at the wrong step")
    # set chosen leader as active
    picked_leader = BirdLeader.objects.get(player=player, leader=leader)
    picked_leader.active = True
    picked_leader.save()

    bird_setup.step = BirdsSimpleSetup.Steps.PENDING_CONFIRMATION
    bird_setup.save()


@transaction.atomic
def confirm_completed_setup(player: Player):
    setup = BirdsSimpleSetup.objects.get(player=player)
    if setup.step != BirdsSimpleSetup.Steps.PENDING_CONFIRMATION:
        raise ValueError("this has been triggered at the wrong step")
    setup.step = BirdsSimpleSetup.Steps.COMPLETED
    setup.save()
    # move to next step in general setup (next player, perhaps)
    simple_setup = GameSimpleSetup.objects.get(game=player.game)
    simple_setup.status = next_choice(
        GameSimpleSetup.GameSetupStatus, simple_setup.status
    )
    simple_setup.save()
