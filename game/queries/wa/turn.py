from game.models.game_models import Faction, Player
from game.models.wa.turn import WABirdsong, WADaylight, WAEvening, WATurn
from game.queries.general import get_current_player


def validate_turn(player: Player) -> WATurn:
    """returns the turn if it is the player's turn, else raises ValueError"""
    current_player = get_current_player(player.game)
    if current_player != player:
        raise ValueError("Not this player's turn")
    if current_player.faction != Faction.WOODLAND_ALLIANCE:
        raise ValueError("This player is not Woodland Alliance")
    wa_turn = WATurn.objects.filter(player=player).order_by("-turn_number").first()
    if wa_turn is None:
        raise ValueError("No turns found for this Woodland Alliance player")
    return wa_turn


def get_phase(player: Player) -> WABirdsong | WADaylight | WAEvening:
    """returns the current phase of the turn, raising
    if not players turn or if turn is  completed.
    """
    # get most recent turn
    wa_turn = validate_turn(player)
    # get phase
    birdsong = WABirdsong.objects.get(turn=wa_turn)
    daylight = WADaylight.objects.get(turn=wa_turn)
    evening = WAEvening.objects.get(turn=wa_turn)
    if birdsong.step != WABirdsong.WABirdsongSteps.COMPLETED:
        return birdsong
    elif daylight.step != WADaylight.WADaylightSteps.COMPLETED:
        return daylight
    else:
        return evening


def validate_phase(
    player: Player, phase_type: type[WABirdsong | WADaylight | WAEvening]
) -> WABirdsong | WADaylight | WAEvening:
    """returns the phase if it is the given phase, else raises ValueError
    also validates turn and player
    """
    mapper = {
        WABirdsong: "Not Birdsong phase",
        WADaylight: "Not Daylight phase",
        WAEvening: "Not Evening phase",
    }
    player_phase = get_phase(player)
    if phase_type != type(player_phase):
        raise ValueError(mapper[phase_type])
    return player_phase


def validate_step(
    player: Player,
    step: (
        WABirdsong.WABirdsongSteps
        | WADaylight.WADaylightSteps
        | WAEvening.WAEveningSteps
    ),
) -> WABirdsong.WABirdsongSteps | WADaylight.WADaylightSteps | WAEvening.WAEveningSteps:
    """returns the step if it is the given step, else raises ValueError
    also validates turn and player
    """
    mapper = {
        WABirdsong.WABirdsongSteps.REVOLT: "Not Revolt step",
        WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY: "Not Spread Sympathy step",
        WABirdsong.WABirdsongSteps.COMPLETED: "Not Birdsong Completed step",
        WADaylight.WADaylightSteps.ACTIONS: "Not Daylight actions step",
        WADaylight.WADaylightSteps.COMPLETED: "Not Daylight completed step",
        WAEvening.WAEveningSteps.MILITARY_OPERATIONS: "Not Military Operations step",
        WAEvening.WAEveningSteps.DRAWING: "Not Drawing step",
        WAEvening.WAEveningSteps.DISCARDING: "Not Discarding step",
        WAEvening.WAEveningSteps.COMPLETED: "Not Evening completed step",
    }
    player_phase = get_phase(player)
    if step != player_phase.step:
        raise ValueError(mapper[step])
    return player_phase.step
