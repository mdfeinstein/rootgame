from game.models.game_models import Player, Warrior
from django.db.models import QuerySet

from game.models.wa.player import OfficerEntry


def get_warriors_in_supply(player: Player) -> QuerySet[Warrior]:
    """returns the warriors in the player's supply
    -- excludes warriors on the board
    -- excludes warriors in the officer box
    """
    return Warrior.objects.filter(player=player, clearing=None, officer__isnull=True)
