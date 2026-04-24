from django.db import transaction
from typing import cast

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Clearing, Faction, Piece, Player, Suit
from game.models.wa.buildings import WABase
from game.models.wa.player import OfficerEntry
from game.models.wa.tokens import WASympathy
from game.queries.general import validate_player_has_card_in_hand
from game.queries.wa.crafting import validate_crafting_pieces_satisfy_requirements
from game.queries.wa.turn import validate_step, get_phase
from game.transactions.general import craft_card, move_warriors, place_piece_from_supply_into_clearing
from game.transactions.wa.supporters import add_officer
from game.models.wa.turn import WADaylight


@transaction.atomic
def wa_craft_card(player: Player, card: CardsEP, crafting_pieces: list[WASympathy]):
    """crafts a card with the given symapthy tokens."""
    validate_step(player, WADaylight.WADaylightSteps.ACTIONS)
    card_in_hand = validate_player_has_card_in_hand(player, card)
    if not validate_crafting_pieces_satisfy_requirements(player, card, crafting_pieces):
        raise ValueError("Not enough crafting pieces to craft card")
    card_model = card_in_hand.card
    craft_card(card_in_hand, cast(list[Piece], crafting_pieces))

    from game.serializers.logs.general import log_craft, get_current_phase_log

    log_craft(
        player.game,
        player,
        card_model,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def training(player: Player, card: CardsEP):
    """trains an officer using the given card
    -- card suit must match a base on the board
    """
    card_suit = Suit(card.value.suit.value)
    card_in_hand = validate_player_has_card_in_hand(player, card)
    matching_base = WABase.objects.filter(
        player=player, suit=card_suit, building_slot__isnull=False
    ).exists()
    if not matching_base and card_suit != Suit.WILD:
        raise ValueError("Suit does not match a base on the board")
    add_officer(player)

    from game.serializers.logs.wa import log_wa_train
    from game.serializers.logs.general import get_current_phase_log

    log_wa_train(
        player.game,
        player,
        card_in_hand.card,
        parent=get_current_phase_log(player.game, player),
    )

    from game.transactions.general import discard_card_from_hand
    discard_card_from_hand(player, card_in_hand)


@transaction.atomic
def operation_move(
    player: Player, start_clearing: Clearing, end_clearing: Clearing, count: int
):
    """moves warriors from start_clearing to end_clearing"""
    officer = OfficerEntry.objects.filter(player=player, used=False).first()
    if officer is None:
        raise ValueError("No unused officers")
    officer.used = True
    officer.save()
    move_warriors(player, start_clearing, end_clearing, count)

    from game.serializers.logs.general import log_move, get_current_phase_log

    log_move(
        player.game,
        player,
        count,
        start_clearing.clearing_number,
        end_clearing.clearing_number,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def operation_battle(player: Player, defender: Player, clearing: Clearing):
    """battles the given defender in the given clearing"""
    officer = OfficerEntry.objects.filter(player=player, used=False).first()
    if officer is None:
        raise ValueError("No unused officers")
    officer.used = True
    officer.save()

    from game.transactions.battle import start_battle, log_battle_start

    battle = start_battle(player.game, Faction(player.faction), Faction(defender.faction), clearing)

    from game.serializers.logs.wa import log_wa_military_operation
    from game.serializers.logs.general import get_current_phase_log

    parent = log_wa_military_operation(
        player.game,
        player,
        "Battle",
        parent=get_current_phase_log(player.game, player),
    )

    log_battle_start(battle, player, parent=parent)


@transaction.atomic
def operation_recruit(player: Player, clearing: Clearing):
    """recruits warriors at the given clearing"""
    officer = OfficerEntry.objects.filter(player=player, used=False).first()
    if officer is None:
        raise ValueError("No unused officers")
    if not WABase.objects.filter(
        player=player, building_slot__clearing=clearing
    ).exists():
        raise ValueError("No base in that clearing")
    officer.used = True
    officer.save()

    from game.queries.wa.warriors import get_warriors_in_supply

    warrior = get_warriors_in_supply(player).first()
    if warrior is None:
        raise ValueError("No warriors in supply")
    place_piece_from_supply_into_clearing(warrior, clearing)

    from game.serializers.logs.wa import log_wa_military_operation
    from game.serializers.logs.general import get_current_phase_log

    log_wa_military_operation(
        player.game,
        player,
        "Recruit",
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def operation_organize(player: Player, clearing: Clearing):
    """Organize in the given clearing by removing a warrior and placing a sympathy there"""
    from game.models.game_models import Warrior
    from game.transactions.wa.birdsong import place_sympathy

    officer = OfficerEntry.objects.filter(player=player, used=False).first()
    if officer is None:
        raise ValueError("No unused officers")
    warrior = Warrior.objects.filter(clearing=clearing, player=player).first()
    if warrior is None:
        raise ValueError("No warrior in that clearing")
    officer.used = True
    officer.save()
    score_before = player.score

    warrior.clearing = None
    warrior.save()
    place_sympathy(player, clearing)

    player.refresh_from_db()
    points_scored = player.score - score_before

    from game.serializers.logs.wa import log_wa_organize
    from game.serializers.logs.general import get_current_phase_log

    log_wa_organize(
        player.game,
        player,
        clearing.clearing_number,
        points_scored,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def end_daylight_actions(player: Player):
    from game.queries.wa.turn import get_phase
    from game.transactions.wa.turn import next_step

    assert player.faction == "wa", "Not WA player"
    daylight = get_phase(player)
    assert isinstance(daylight, WADaylight)
    next_step(player)
