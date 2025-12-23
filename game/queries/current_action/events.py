from django.urls import reverse
from game.models.events.battle import Battle
from game.models.events.event import Event, EventType
from game.models.game_models import Game


def get_current_event_action(game: Game) -> str | None:
    """returns the current event action for the game, or None if no event"""
    event = get_current_event(game)
    print(f"event: {event}")
    if event is None:
        return None
    print(f"event.type: {event.type}")
    print(f"event.is_resolved: {event.is_resolved}")
    match event.type:
        case EventType.BATTLE:
            return reverse("battle")
        case EventType.FIELD_HOSPITAL:
            return reverse("field-hospital")
        case EventType.TURMOIL:
            return reverse("turmoil")
        case EventType.OUTRAGE:
            return reverse("outrage")
        case _:
            raise ValueError("Invalid event type")


def get_current_event(game: Game) -> Event | None:
    """returns the current event for the game"""
    # get oldest event
    event = (
        Event.objects.filter(game=game, is_resolved=False)
        .order_by("created_at")
        .first()
    )
    return event
