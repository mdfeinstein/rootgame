from game.models.events.cats import FieldHospitalEvent
from game.models.game_models import Faction, Player
from game.models.events.event import Event, EventType
from game.queries.current_action.events import get_current_event


def get_field_hospital_event(player: Player) -> FieldHospitalEvent:
    """returns the current field hospital event"""
    assert player.faction == Faction.CATS, "Not a cats player"
    event = get_current_event(player.game)
    if event is None:
        raise ValueError("No events")
    if event.type != EventType.FIELD_HOSPITAL:
        raise ValueError("Not a field hospital event")
    return FieldHospitalEvent.objects.get(event=event)
