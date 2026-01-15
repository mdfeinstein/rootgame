from game.models.wa.tokens import WASympathy
from game.models.game_models import Player
from django.db.models import QuerySet


def sympathy_at_clearing_number(player: Player, clearing_number: int) -> WASympathy:
    """returns the sympathy at the given clearing number,
    raises value error if no sympathy at that clearing number"""
    try:
        sympathy = WASympathy.objects.get(
            player=player, clearing__clearing_number=clearing_number
        )
    except WASympathy.DoesNotExist as e:
        raise ValueError(f"No sympathy token at clearing {clearing_number}")
    return sympathy
