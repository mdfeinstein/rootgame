from game.models.game_models import Player
from game.models.wa.player import OfficerEntry


def get_unused_officer_count(player: Player) -> int:
    """returns the number of unused officers in the players officer box"""
    return OfficerEntry.objects.filter(player=player, used=False).count()
