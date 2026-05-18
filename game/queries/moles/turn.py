from game.models.game_models import Faction, Player
from game.models.moles.turn import MoleBirdsong, MoleDaylight, MoleEvening, MoleTurn
from game.queries.general import get_current_player
from game.errors import UnavailableActionError, InternalGameError


def validate_turn(player: Player) -> MoleTurn:
    """returns the turn if it is the player's turn, else raises error"""
    current_player = get_current_player(player.game)
    if current_player != player:
        raise UnavailableActionError("Not this player's turn")
    if current_player.faction != Faction.MOLES:
        raise UnavailableActionError("This player is not the Moles")
    mole_turn = MoleTurn.objects.filter(player=player).order_by("-turn_number").first()
    if mole_turn is None:
        raise InternalGameError("No turns found for this Moles player")
    return mole_turn


def get_phase(player: Player) -> MoleBirdsong | MoleDaylight | MoleEvening:
    """returns the current phase of the turn, raising
    if not players turn or if turn is completed.
    """
    # get most recent turn
    mole_turn = validate_turn(player)
    # get phase
    birdsong = MoleBirdsong.objects.get(turn=mole_turn)
    daylight = MoleDaylight.objects.get(turn=mole_turn)
    evening = MoleEvening.objects.get(turn=mole_turn)
    if birdsong.step != MoleBirdsong.MoleBirdsongSteps.COMPLETED:
        return birdsong
    elif daylight.step != MoleDaylight.MoleDaylightSteps.COMPLETED:
        return daylight
    else:
        return evening


def validate_phase(
    player: Player, phase_type: type[MoleBirdsong | MoleDaylight | MoleEvening]
) -> MoleBirdsong | MoleDaylight | MoleEvening:
    """returns the phase if it is the given phase, else raises UnavailableActionError"""
    mapper = {
        MoleBirdsong: "Not Birdsong phase",
        MoleDaylight: "Not Daylight phase",
        MoleEvening: "Not Evening phase",
    }
    player_phase = get_phase(player)
    if phase_type != type(player_phase):
        raise UnavailableActionError(mapper[phase_type])
    return player_phase


def validate_step(
    player: Player,
    step: (
        MoleBirdsong.MoleBirdsongSteps
        | MoleDaylight.MoleDaylightSteps
        | MoleEvening.MoleEveningSteps
    ),
) -> None:
    """Validate player is in the given step, raise UnavailableActionError if not."""
    player_phase = get_phase(player)
    if step != player_phase.step:
        # Avoid collisions between different phases with same step values
        if isinstance(player_phase, MoleBirdsong):
            birdsong_mapper = {
                MoleBirdsong.MoleBirdsongSteps.PLACE_WARRIORS: "Not Place Warriors step",
                MoleBirdsong.MoleBirdsongSteps.COMPLETED: "Not Birdsong Completed step",
            }
            raise UnavailableActionError(birdsong_mapper.get(step, "Invalid Birdsong step"))
        elif isinstance(player_phase, MoleDaylight):
            daylight_mapper = {
                MoleDaylight.MoleDaylightSteps.ACTIONS: "Not Actions step",
                MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS: "Not Minister Actions step",
                MoleDaylight.MoleDaylightSteps.SWAY_MINISTER: "Not Sway Minister step",
                MoleDaylight.MoleDaylightSteps.COMPLETED: "Not Daylight completed step",
            }
            raise UnavailableActionError(daylight_mapper.get(step, "Invalid Daylight step"))
        elif isinstance(player_phase, MoleEvening):
            evening_mapper = {
                MoleEvening.MoleEveningSteps.PROCESS_REVEALED_CARDS: "Not Process Revealed Cards step",
                MoleEvening.MoleEveningSteps.CRAFT: "Not Craft step",
                MoleEvening.MoleEveningSteps.DRAW: "Not Draw step",
                MoleEvening.MoleEveningSteps.DISCARD: "Not Discard step",
                MoleEvening.MoleEveningSteps.COMPLETED: "Not Evening completed step",
            }
            raise UnavailableActionError(evening_mapper.get(step, "Invalid Evening step"))
        else:
            raise UnavailableActionError("Invalid phase")
