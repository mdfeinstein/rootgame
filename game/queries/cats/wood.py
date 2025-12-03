from game.models.cats.buildings import Sawmill
from game.models.game_models import Game, Player


def get_unused_sawmill_by_clearing_number(
    player: Player, clearing_number: int
) -> Sawmill | None:
    """returns an unused sawmill at the given clearing number"""
    sawmill = Sawmill.objects.filter(player=player, used=False).first()
    return sawmill
