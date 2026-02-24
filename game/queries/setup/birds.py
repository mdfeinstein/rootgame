from game.models.cats.tokens import CatKeep
from game.models.game_models import Clearing, Game, Player


def validate_corner(game: Game, corner: Clearing):
    """checks that the corner is a corner and is diagonally opposite the keep if it is on the board"""
    if corner.clearing_number not in [1, 2, 3, 4]:
        raise ValueError("Clearing number must be 1, 2, 3, or 4 to be a corner")
    try:
        keep = CatKeep.objects.get(player__game=game, clearing__isnull=False)
        opposite_corner_number = ((keep.clearing.clearing_number - 1 + 2) % 4) + 1
    except CatKeep.DoesNotExist:
        opposite_corner_number = None


    if (
        opposite_corner_number is not None
        and opposite_corner_number != corner.clearing_number
    ):
        raise ValueError("Cat's Keep is not in the opposite corner")

