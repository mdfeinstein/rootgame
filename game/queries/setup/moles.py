from game.models.cats.tokens import CatKeep
from game.models.birds.buildings import BirdRoost
from game.models.game_models import Clearing, Game
from game.errors import IllegalActionError


def validate_corner(game: Game, corner: Clearing):
    """checks that the corner is a valid corner clearing and respects faction positioning rules"""
    if corner.clearing_number not in [1, 2, 3, 4]:
        raise IllegalActionError("Clearing number must be 1, 2, 3, or 4 to be a corner")
    if corner.game != game:
        raise IllegalActionError("Clearing is not in the same game")

    # Find occupied corners and their diagonally opposite corners
    keep_corner = None
    roost_corner = None

    # Check if Cat's Keep is placed in a corner
    try:
        keep = CatKeep.objects.get(player__game=game, clearing__isnull=False)
        if keep.clearing is not None and keep.clearing.clearing_number in [1, 2, 3, 4]:
            keep_corner = keep.clearing.clearing_number
    except CatKeep.DoesNotExist:
        pass

    # Check if Bird's Roost is placed in a corner
    try:
        roost = BirdRoost.objects.get(player__game=game, building_slot__clearing__clearing_number__in=[1, 2, 3, 4])
        if roost.building_slot is not None:
            roost_corner = roost.building_slot.clearing.clearing_number
    except BirdRoost.DoesNotExist:
        pass

    # If only Keep is placed, Moles must use opposite corner
    if keep_corner is not None and roost_corner is None:
        opposite = ((keep_corner - 1 + 2) % 4) + 1
        if corner.clearing_number != opposite:
            raise IllegalActionError(
                f"Cat's Keep is in corner {keep_corner}, "
                f"Moles must place burrow in opposite corner {opposite}"
            )

    # If only Roost is placed, Moles must use opposite corner
    if roost_corner is not None and keep_corner is None:
        opposite = ((roost_corner - 1 + 2) % 4) + 1
        if corner.clearing_number != opposite:
            raise IllegalActionError(
                f"Bird's Roost is in corner {roost_corner}, "
                f"Moles must place burrow in opposite corner {opposite}"
            )

    # If both are placed, Moles can use any remaining corner
    if keep_corner is not None and roost_corner is not None:
        occupied = {keep_corner, roost_corner}
        if corner.clearing_number in occupied:
            raise IllegalActionError(
                f"Corner {corner.clearing_number} is already occupied by another faction"
            )
