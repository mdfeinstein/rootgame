from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening, BirdTurn
from game.models.events.birds import TurmoilEvent
from game.models.events.event import Event, EventType
from game.models.game_models import Faction, Player
from game.queries.current_action.events import get_current_event
from game.queries.general import get_current_player


def validate_turn(player: Player) -> BirdTurn:
    """returns the turn if it is the player's turn, else raises ValueError"""
    current_player = get_current_player(player.game)
    if current_player != player:
        raise ValueError("Not this player's turn")
    if current_player.faction != Faction.BIRDS:
        raise ValueError("This player is not birds")
    bird_turn = BirdTurn.objects.filter(player=player).order_by("-turn_number").first()
    if bird_turn is None:
        raise ValueError("No turns found for this birdsplayer")
    return bird_turn


def get_phase(player: Player) -> BirdBirdsong | BirdDaylight | BirdEvening:
    """returns the current phase of the turn, raising
    if not players turn or if turn is  completed.
    """
    # get most recent turn
    bird_turn = validate_turn(player)
    # get phase
    birdsong = BirdBirdsong.objects.get(turn=bird_turn)
    daylight = BirdDaylight.objects.get(turn=bird_turn)
    evening = BirdEvening.objects.get(turn=bird_turn)
    if birdsong.step != BirdBirdsong.BirdBirdsongSteps.COMPLETED:
        return birdsong
    elif daylight.step != BirdDaylight.BirdDaylightSteps.COMPLETED:
        return daylight
    else:
        return evening


def validate_phase(
    player: Player, phase_type: type[BirdBirdsong | BirdDaylight | BirdEvening]
) -> BirdBirdsong | BirdDaylight | BirdEvening:
    """returns the phase if it is the given phase, else raises ValueError
    also validates turn and player
    """
    mapper = {
        BirdBirdsong: "Not Birdsong phase",
        BirdDaylight: "Not Daylight phase",
        BirdEvening: "Not Evening phase",
    }
    player_phase = get_phase(player)
    if phase_type != type(player_phase):
        raise ValueError(mapper[phase_type])
    return player_phase


def validate_step(
    player: Player,
    step: (
        BirdBirdsong.BirdBirdsongSteps
        | BirdDaylight.BirdDaylightSteps
        | BirdEvening.BirdEveningSteps
    ),
) -> (
    BirdBirdsong.BirdBirdsongSteps
    | BirdDaylight.BirdDaylightSteps
    | BirdEvening.BirdEveningSteps
):
    """returns the step if it is the given step, else raises ValueError
    also validates turn and player
    """
    mapper = {
        BirdBirdsong.BirdBirdsongSteps.EMERGENCY_DRAWING: "Not Emergency Drawing step",
        BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE: "Not Add to Decree step",
        BirdBirdsong.BirdBirdsongSteps.EMERGENCY_ROOSTING: "Not Emergency Roosting step",
        BirdBirdsong.BirdBirdsongSteps.COMPLETED: "Not Birdsong Completed step",
        BirdDaylight.BirdDaylightSteps.CRAFTING: "Not Crafting step",
        BirdDaylight.BirdDaylightSteps.RECRUITING: "Not Recruiting step",
        BirdDaylight.BirdDaylightSteps.MOVING: "Not Moving Step",
        BirdDaylight.BirdDaylightSteps.BATTLING: "Not battling step",
        BirdDaylight.BirdDaylightSteps.BUILDING: "Not building step",
        BirdDaylight.BirdDaylightSteps.COMPLETED: "Not Daylight completed step",
        BirdEvening.BirdEveningSteps.SCORING: "Not Evening scoring step",
        BirdEvening.BirdEveningSteps.DRAWING: "Not Evening drawing step",
        BirdEvening.BirdEveningSteps.DISCARDING: "Not Evening discarding step",
        BirdEvening.BirdEveningSteps.COMPLETED: "Not Evening completedstep",
    }
    player_phase = get_phase(player)
    if step != player_phase.step:
        raise ValueError(mapper[step])
    return player_phase.step


def get_turmoil_event(player: Player) -> TurmoilEvent:
    """get current turmoil event"""
    assert player.faction == Faction.BIRDS, "Not a birds player"
    event = get_current_event(player.game)
    if event is None:
        raise ValueError("No events")
    if event.type != EventType.TURMOIL:
        raise ValueError("Not a turmoil event")
    return TurmoilEvent.objects.get(event=event)
