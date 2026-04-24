from django.db import transaction
from django.apps import apps
from django.db.models import QuerySet
from typing import cast

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.cats.buildings import CatBuildingTypes, Recruiter, Workshop
from game.models.cats.tokens import CatWood
from game.models.game_models import (
    Building,
    Clearing,
    Faction,
    Player,
    Suit,
    Warrior,
)
from game.queries.cats.building import (
    get_score_after_placement,
    get_usable_wood_for_building,
    get_wood_cost,
)
from game.queries.cats.crafting import validate_crafting_pieces_satisfy_requirements
from game.queries.cats.recruit import (
    is_enough_reserve,
    is_recruit_used,
    unused_recruiters,
)
from game.queries.cats.turn import get_actions_remaining, get_phase
from game.queries.general import (
    get_current_player,
    get_player_hand_size,
    validate_player_has_card_in_hand,
)
from game.transactions.general import (
    craft_card,
    discard_card_from_hand,
    move_warriors,
    place_piece_from_supply_into_clearing,
    raise_score,
)


@transaction.atomic
def build_building(
    player: Player,
    building_type: CatBuildingTypes,
    clearing: Clearing,
    wood_tokens: list[CatWood],
):
    """builds a building of the given type in the given clearing using the given wood tokens"""
    game = player.game
    if clearing.game != game:
        raise ValueError("All objects must belong to the same game")
    for token in wood_tokens:
        if token.player != player:
            raise ValueError("All tokens must belong to the same player")
    if len(wood_tokens) != len(set(wood_tokens)):
        raise ValueError("Duplicate tokens provided")

    required_wood = get_wood_cost(player, building_type)
    if required_wood is None:
        raise ValueError("No building of that type in supply")
    if len(wood_tokens) < required_wood:
        raise ValueError("Not enough wood tokens provided to build this building")

    available_wood = get_usable_wood_for_building(player, building_type, clearing)
    if available_wood is None:
        raise ValueError("Not enough connected wood to build")
    available_wood = set(available_wood)
    if not all([token in available_wood for token in wood_tokens]):
        raise ValueError("provided wood tokens are not all connected to the clearing")

    scoring = get_score_after_placement(player, building_type)
    if scoring is None:
        raise ValueError("Building type not in supply. how did we get this far?")
    raise_score(player, scoring)
    building_model = apps.get_model("game", building_type.value)
    building = building_model.objects.filter(player=player, building_slot=None).first()
    if building is None:
        raise ValueError("No building of that type in supply")
    assert isinstance(building, Building)
    place_piece_from_supply_into_clearing(building, clearing)

    for token in wood_tokens:
        token.clearing = None
        token.save()

    from game.serializers.logs.cats import log_cats_build
    from game.serializers.logs.general import get_current_phase_log

    log_cats_build(
        player.game,
        player,
        building_type.value,
        clearing.clearing_number,
        required_wood,
        scoring,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def action_used(player: Player):
    """reduces the actions remaining during cats daylight stage by 1"""
    from game.models.cats.turn import CatDaylight

    daylight = get_phase(player)
    if type(daylight) != CatDaylight:
        raise ValueError("Not Daylight phase")
    if daylight.actions_left == 0:
        raise ValueError("No actions remaining")
    daylight.actions_left -= 1
    daylight.save()


@transaction.atomic
def overwork(player: Player, clearing: Clearing, card: CardsEP):
    """overworks a sawmill in the given clearing, discarding the card from the player's hand"""
    from game.queries.cats.wood import get_sawmills_by_suit

    hand_entry = validate_player_has_card_in_hand(player, card)
    card_model = hand_entry.card

    sawmills = get_sawmills_by_suit(player, card.value.suit)
    if not sawmills.filter(building_slot__clearing=clearing).exists():
        raise ValueError("No sawmill in that clearing")

    wood_token = CatWood.objects.filter(clearing=None, player=player).first()
    if wood_token is None:
        raise ValueError("No wood tokens left to overwork")

    place_piece_from_supply_into_clearing(wood_token, clearing)
    discard_card_from_hand(player, hand_entry)
    action_used(player)

    from game.serializers.logs.cats import log_cats_overwork
    from game.serializers.logs.general import get_current_phase_log

    log_cats_overwork(
        player.game,
        player,
        clearing.clearing_number,
        card_model,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def birds_for_hire(player: Player, card: CardsEP):
    """uses the given card to gain an action"""
    from game.models.cats.turn import CatDaylight

    hand_entry = validate_player_has_card_in_hand(player, card)
    card_model = hand_entry.card

    if card.value.suit != Suit.WILD:
        raise ValueError("Not a bird card")

    daylight = get_phase(player)
    if type(daylight) != CatDaylight:
        raise ValueError("Not Daylight phase")

    daylight.actions_left += 1
    daylight.save()
    discard_card_from_hand(player, hand_entry)

    from game.serializers.logs.cats import log_cats_birds_for_hire
    from game.serializers.logs.general import get_current_phase_log

    log_cats_birds_for_hire(
        player.game,
        player,
        card_model,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def cat_craft_card(player: Player, card: CardsEP, crafting_pieces: list[Workshop]):
    card_in_hand = validate_player_has_card_in_hand(player, card)
    card_model = card_in_hand.card
    if not validate_crafting_pieces_satisfy_requirements(player, card, crafting_pieces):
        raise ValueError("Not enough crafting pieces to craft card")
    craft_card(card_in_hand, crafting_pieces)

    from game.serializers.logs.general import log_craft, get_current_phase_log

    log_craft(
        player.game,
        player,
        card_model,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def cat_recruit(player: Player, recruiters: QuerySet[Recruiter]):
    """recruits warriors from the given recruiter stations"""
    if is_recruit_used(player):
        raise ValueError("Recruit has already been used this turn")
    if recruiters.count() == 0:
        raise ValueError("No recruiters selected to recruit from")

    if not all(
        [
            (not recruiter.used and recruiter.building_slot is not None)
            for recruiter in recruiters
        ]
    ):
        raise ValueError("Not all recruiters have been used")

    if Warrior.objects.filter(player=player, clearing=None).count() < len(recruiters):
        raise ValueError(
            f"Not enough warriors in supply to recruit at {len(recruiters)} recruiter stations"
        )

    if get_current_player(player.game) != player:
        raise ValueError("Not this player's turn")

    from game.models.cats.turn import CatDaylight

    daylight = get_phase(player)
    if type(daylight) != CatDaylight:
        raise ValueError("Not Daylight phase")
    if daylight.step != CatDaylight.CatDaylightSteps.ACTIONS:
        raise ValueError("Not actions step")

    if get_actions_remaining(player) < 1:
        raise ValueError("No actions remaining")

    for recruiter in recruiters:
        warrior = Warrior.objects.filter(clearing=None, player=player).first()
        assert warrior is not None, "no warriors left to place"
        place_piece_from_supply_into_clearing(warrior, recruiter.building_slot.clearing)
        recruiter.used = True
        recruiter.save()

    daylight.recruit_used = True
    daylight.actions_left -= 1
    daylight.save()

    from game.serializers.logs.cats import log_cats_recruit
    from game.serializers.logs.general import get_current_phase_log

    clearings_dict = {}
    for r in recruiters:
        c_num = str(r.building_slot.clearing.clearing_number)
        clearings_dict[c_num] = clearings_dict.get(c_num, 0) + 1
    log_cats_recruit(
        player.game,
        player,
        len(recruiters),
        clearings_dict,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def cat_recruit_all(player: Player):
    """recruits at every recruiter station on the board"""
    recruiters = unused_recruiters(player)
    if is_enough_reserve(player):
        cat_recruit(player, recruiters)
    else:
        raise ValueError("Not enough recruiters on the board to recruit all")


@transaction.atomic
def end_crafting_step(player: Player):
    """ends the current crafting step, moving to the next step"""
    from game.models.cats.turn import CatDaylight

    daylight = get_phase(player)
    assert type(daylight) == CatDaylight, "Not Daylight phase"
    assert daylight.step == CatDaylight.CatDaylightSteps.CRAFTING, "Not crafting step"
    from game.transactions.cats.turn import next_step
    next_step(player)


@transaction.atomic
def end_action_step(player: Player):
    """ends the current action step, moving to the next step"""
    from game.models.cats.turn import CatDaylight

    daylight = get_phase(player)
    assert type(daylight) == CatDaylight, "Not Daylight phase"
    assert daylight.step == CatDaylight.CatDaylightSteps.ACTIONS, "Not actions step"
    from game.transactions.cats.turn import next_step
    next_step(player)


@transaction.atomic
def cat_march(player: Player, origin: Clearing, destination: Clearing, count: int):
    """performs a march action"""
    from game.models.cats.turn import CatDaylight

    if get_current_player(player.game) != player:
        raise ValueError("Not this player's turn")
    daylight = get_phase(player)
    if type(daylight) != CatDaylight:
        raise ValueError("Not Daylight phase")

    from game.serializers.logs.general import log_move, get_current_phase_log
    from game.serializers.logs.cats import log_cats_march, get_current_march_log

    if not daylight.midmarch:
        if daylight.actions_left < 1:
            raise ValueError("No actions remaining")

        phase_log = get_current_phase_log(player.game, player)
        march_log = log_cats_march(player.game, player, parent=phase_log)
        log_move(
            player.game,
            player,
            origin.clearing_number,
            destination.clearing_number,
            count,
            parent=march_log,
        )

        move_warriors(player, origin, destination, count)

        daylight.actions_left -= 1
        daylight.midmarch = True
        daylight.save()
    else:
        march_log = get_current_march_log(player.game, player)
        log_move(
            player.game,
            player,
            origin.clearing_number,
            destination.clearing_number,
            count,
            parent=march_log,
        )

        move_warriors(player, origin, destination, count)
        daylight.midmarch = False
        daylight.save()


@transaction.atomic
def cat_battle(player: Player, defender: Player, clearing: Clearing):
    from game.transactions.battle import start_battle

    from game.models.cats.turn import CatDaylight

    daylight = get_phase(player)
    if type(daylight) != CatDaylight:
        raise ValueError("Not Daylight phase")
    battle = start_battle(
        player.game, Faction(player.faction), Faction(defender.faction), clearing
    )
    daylight.actions_left -= 1
    daylight.save()

    from game.transactions.battle import log_battle_start
    from game.serializers.logs.general import get_current_phase_log

    log_battle_start(
        battle,
        player,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def cat_build(
    player: Player,
    building_type: CatBuildingTypes,
    clearing: Clearing,
    wood_tokens: list[CatWood],
):
    build_building(player, building_type, clearing, wood_tokens)
    action_used(player)
