from game.models.events.event import Event, EventType
from game.models.events.wa import OutrageEvent
from game.models.game_models import Clearing, HandEntry, Player, Suit
from django.db import transaction

from game.serializers.general_serializers import PlayerPrivateSerializer


@transaction.atomic
def create_outrage_event(
    clearing: Clearing,
    removing_player: Player,
    removed_player: Player,
    trigger_type: str = "",
):
    """creates an outrage event when a player removes a token"""
    from game.transactions.wa import draw_card_to_supporters
    from game.queries.general import get_current_turn_number

    event = Event.objects.create(game=clearing.game, type=EventType.OUTRAGE)
    turn_number = get_current_turn_number(clearing.game)

    outrage_event = OutrageEvent.objects.create(
        event=event,
        outraged_player=removed_player,
        outrageous_player=removing_player,
        suit=clearing.suit,
        turn_number=turn_number,
    )
    # if player does not have correct suit or wild, resolve by drawing and showing hand
    has_suit = HandEntry.objects.filter(
        player=removing_player, card__suit=clearing.suit
    ).exists()
    has_wild = HandEntry.objects.filter(
        player=removing_player, card__suit=Suit.WILD
    ).exists()
    if not has_suit and not has_wild:
        # show hand, player draws from deck to supporters
        serializer = PlayerPrivateSerializer(removing_player)
        outrage_event.hand = serializer.data
        draw_card_to_supporters(removed_player)
        outrage_event.card_given = False
        outrage_event.hand_shown = True
        outrage_event.save()
        event.is_resolved = True
        event.save()

    # Log the Outrage trigger
    from game.serializers.logs.wa import log_wa_outrage
    from game.serializers.logs.general import get_active_phase_log

    log_wa_outrage(
        clearing.game,
        removed_player,
        removing_player,
        clearing.clearing_number,
        outrage_event.card_given,
        outrage_event.hand_shown,
        trigger_type=trigger_type,
        outrage_event=outrage_event,
        parent=get_active_phase_log(clearing.game),
    )
