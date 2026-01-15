from game.transactions.wa import draw_card_from_deck_to_supporter_pile
from game.models.events.event import Event, EventType
from game.models.events.wa import OutrageEvent
from game.models.game_models import Clearing, HandEntry, Player, Suit
from django.db import transaction

from game.serializers.general_serializers import PlayerPrivateSerializer
from game.transactions.general import draw_card_from_deck


@transaction.atomic
def create_outrage_event(
    clearing: Clearing, removing_player: Player, removed_player: Player
):
    """creates an outrage event when a player removes a token"""
    event = Event.objects.create(game=clearing.game, type=EventType.OUTRAGE)
    outrage_event = OutrageEvent.objects.create(
        event=event,
        outraged_player=removed_player,
        outrageous_player=removing_player,
        suit=clearing.suit,
    )
    # if player does not have correct suit or wild, resolve by drawing and showing hand
    has_suit = HandEntry.objects.filter(
        player=removing_player, card__suit=clearing.suit
    ).exists()
    has_wild = HandEntry.objects.filter(
        player=removing_player, card__suit=Suit.WILD
    ).exists()
    if not has_suit and not has_wild:
        # show hand, player draws from deck into supporter pile
        serializer = PlayerPrivateSerializer(removing_player)
        outrage_event.hand = serializer.data
        draw_card_from_deck_to_supporter_pile(removed_player)
        outrage_event.card_given = True
        outrage_event.hand_shown = True
        outrage_event.save()
        event.is_resolved = True
        event.save()
