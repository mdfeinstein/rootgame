import random
from django.db import transaction

from game.models.game_models import Player, HandEntry
from game.models.moles.ministers import Minister
from game.models.moles.crown import Crown
from game.models.events.event import Event, EventType
from game.models.events.moles import PriceOfFailureEvent
from game.errors import IllegalActionError, UnavailableActionError
from game.queries.moles.price_of_failure import (
    get_highest_rank_swayed_ministers,
    validate_minister_is_highest_rank,
)
from game.transactions.general import discard_card_from_hand
from game.serializers.general_serializers import CardSerializer
from game.serializers.logs.general import get_current_phase_log
from game.serializers.logs.moles import log_moles_price_of_failure


@transaction.atomic
def trigger_price_of_failure(player: Player):
    """Trigger price of failure when Moles buildings are removed.

    If only one minister of highest rank: auto-resolve immediately.
    If multiple: create PriceOfFailureEvent for player to choose.

    Deduplicates within a removal event using RemovalEventTracker.

    Args:
        player: The Moles player
    """
    from game.queries.general import get_current_removal_tracker

    # Deduplicate: only trigger once per removal event
    tracker = get_current_removal_tracker(player.game)
    if tracker is not None:
        if tracker.price_of_failure_triggered:
            return
        tracker.price_of_failure_triggered = True
        tracker.save()

    highest_rank_ministers = get_highest_rank_swayed_ministers(player)

    if len(highest_rank_ministers) == 0:
        _perform_price_of_failure(player, None)

    elif len(highest_rank_ministers) == 1:
        # Auto-resolve with the only minister of highest rank
        minister = highest_rank_ministers[0]
        _perform_price_of_failure(player, minister)
    else:
        # Multiple ministers of highest rank: create event for player to choose
        event = Event.objects.create(
            game=player.game,
            type=EventType.PRICE_OF_FAILURE,
            is_resolved=False,
        )
        PriceOfFailureEvent.objects.create(event=event)


@transaction.atomic
def resolve_price_of_failure(player: Player, minister_name: Minister.MinisterName):
    """Resolve price of failure by returning a minister to unswayed.

    Args:
        player: The Moles player
        minister_name: The MinisterName to return to unswayed

    Raises:
        UnavailableActionError if no current event.
        IllegalActionError if minister not of highest rank.
    """
    # Validate event exists
    try:
        event = Event.objects.get(
            game=player.game,
            type=EventType.PRICE_OF_FAILURE,
            is_resolved=False,
            price_of_failure__isnull=False,
        )
    except Event.DoesNotExist:
        raise UnavailableActionError("No Price of Failure event pending")

    # Validate minister is of highest rank
    validate_minister_is_highest_rank(player, minister_name)

    # Get minister
    minister = Minister.objects.get(player=player, name=minister_name)

    # Perform the action
    _perform_price_of_failure(player, minister)

    # Mark event as resolved
    event.is_resolved = True
    event.save()


def _perform_price_of_failure(player: Player, minister: Minister | None):
    """Perform the actual price of failure action.

    - Returns minister to unswayed
    - Removes crown from game permanently
    - Discards a random card

    Args:
        player: The Moles player
        minister: The Minister instance to return (or None)
    """
    if minister is not None:
        # Return minister to unswayed
        minister.swayed = False
        minister.save()

    # Discard a random card if hand has cards
    hand_entries = HandEntry.objects.filter(player=player)
    if hand_entries.exists():
        card_entry = random.choice(list(hand_entries))
        card_model = card_entry.card
        discard_card_from_hand(player, card_entry)

        # Log the action
        phase_log = get_current_phase_log(player.game, player)
        log_moles_price_of_failure(
            player.game,
            player,
            CardSerializer(card_model).data,
            minister.name if minister else "",
            parent=phase_log,
        )
