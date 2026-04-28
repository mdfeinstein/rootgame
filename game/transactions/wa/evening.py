from django.db import transaction

from game.models.game_models import Player
from game.models.wa.buildings import WABase
from game.models.wa.turn import WAEvening
from game.queries.general import get_player_hand_size
from game.queries.wa.turn import get_phase, validate_step
from game.transactions.general import draw_card_from_deck_to_hand
from game.errors import UnavailableActionError, IllegalActionError, InternalGameError


@transaction.atomic
def draw_cards(player: Player):
    """draws cards equal to bases on board + 1"""
    evening = get_phase(player)
    assert isinstance(evening, WAEvening)
    validate_step(player, WAEvening.WAEveningSteps.DRAWING)

    cards_to_draw = (
        WABase.objects.filter(player=player, building_slot__isnull=False).count() + 1
    )
    drawn_cards = []
    for _ in range(cards_to_draw):
        hand_entry = draw_card_from_deck_to_hand(player)
        drawn_cards.append(hand_entry.card)

    from game.serializers.logs.general import log_draw, get_current_phase_log

    log_draw(
        player.game,
        player,
        drawn_cards,
        parent=get_current_phase_log(player.game, player),
    )

    from game.transactions.wa.turn import next_step
    next_step(player)


@transaction.atomic
def check_discard_step(player: Player):
    """if over hand limit, exit out so player can handle discarding step"""
    evening = get_phase(player)
    assert isinstance(evening, WAEvening)
    validate_step(player, WAEvening.WAEveningSteps.DISCARDING)

    if get_player_hand_size(player) > 5:
        return

    from game.transactions.wa.turn import next_step
    next_step(player)


@transaction.atomic
def end_evening_operations(player: Player):
    from game.transactions.wa.turn import next_step

    assert player.faction == "wa", "Not WA player"
    evening = get_phase(player)
    assert isinstance(evening, WAEvening)
    next_step(player)
