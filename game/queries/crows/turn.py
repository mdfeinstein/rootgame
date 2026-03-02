from game.models.game_models import Faction, Player
from game.models.crows.turn import CrowBirdsong, CrowDaylight, CrowEvening, CrowTurn
from game.queries.general import get_current_player


def validate_turn(player: Player) -> CrowTurn:
    """returns the turn if it is the player's turn, else raises ValueError"""
    current_player = get_current_player(player.game)
    if current_player != player:
        raise ValueError("Not this player's turn")
    if current_player.faction != Faction.CROWS:
        raise ValueError("This player is not Corvid Conspiracy")
    crow_turn = CrowTurn.objects.filter(player=player).order_by("-turn_number").first()
    if crow_turn is None:
        raise ValueError("No turns found for this Corvid Conspiracy player")
    return crow_turn


def get_phase(player: Player) -> CrowBirdsong | CrowDaylight | CrowEvening:
    """returns the current phase of the turn, raising
    if not players turn or if turn is completed.
    """
    # get most recent turn
    crow_turn = validate_turn(player)
    # get phase
    birdsong = CrowBirdsong.objects.get(turn=crow_turn)
    daylight = CrowDaylight.objects.get(turn=crow_turn)
    evening = CrowEvening.objects.get(turn=crow_turn)
    if birdsong.step != CrowBirdsong.CrowBirdsongSteps.COMPLETED:
        return birdsong
    elif daylight.step != CrowDaylight.CrowDaylightSteps.COMPLETED:
        return daylight
    else:
        return evening


def validate_phase(
    player: Player, phase_type: type[CrowBirdsong | CrowDaylight | CrowEvening]
) -> CrowBirdsong | CrowDaylight | CrowEvening:
    """returns the phase if it is the given phase, else raises ValueError
    also validates turn and player
    """
    mapper = {
        CrowBirdsong: "Not Birdsong phase",
        CrowDaylight: "Not Daylight phase",
        CrowEvening: "Not Evening phase",
    }
    player_phase = get_phase(player)
    if phase_type != type(player_phase):
        raise ValueError(mapper[phase_type])
    return player_phase


def validate_step(
    player: Player,
    step: (
        CrowBirdsong.CrowBirdsongSteps
        | CrowDaylight.CrowDaylightSteps
        | CrowEvening.CrowEveningSteps
    ),
) -> (
    CrowBirdsong.CrowBirdsongSteps
    | CrowDaylight.CrowDaylightSteps
    | CrowEvening.CrowEveningSteps
):
    """returns the step if it is the given step, else raises ValueError
    also validates turn and player
    """
    player_phase = get_phase(player)
    if step != player_phase.step:
        # Avoid collisions between different phases with same step values
        if isinstance(player_phase, CrowBirdsong):
            birdsong_mapper = {
                CrowBirdsong.CrowBirdsongSteps.CRAFT: "Not Craft step",
                CrowBirdsong.CrowBirdsongSteps.FLIP: "Not Flip step",
                CrowBirdsong.CrowBirdsongSteps.RECRUIT: "Not Recruit step",
                CrowBirdsong.CrowBirdsongSteps.COMPLETED: "Not Birdsong Completed step",
            }
            raise ValueError(birdsong_mapper.get(step, "Invalid Birdsong step"))
        elif isinstance(player_phase, CrowDaylight):
            daylight_mapper = {
                CrowDaylight.CrowDaylightSteps.ACTIONS: "Not Daylight actions step",
                CrowDaylight.CrowDaylightSteps.COMPLETED: "Not Daylight completed step",
            }
            raise ValueError(daylight_mapper.get(step, "Invalid Daylight step"))
        elif isinstance(player_phase, CrowEvening):
            evening_mapper = {
                CrowEvening.CrowEveningSteps.EXERT: "Not Exert step",
                CrowEvening.CrowEveningSteps.DRAWING: "Not Drawing step",
                CrowEvening.CrowEveningSteps.DISCARDING: "Not Discarding step",
                CrowEvening.CrowEveningSteps.COMPLETED: "Not Evening completed step",
            }
            raise ValueError(evening_mapper.get(step, "Invalid Evening step"))
        else:
            raise ValueError("Invalid phase")
    return player_phase.step
