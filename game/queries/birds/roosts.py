from game.models.birds.buildings import BirdRoost
from game.models.game_models import Player
from django.db.models import QuerySet


def get_roosts_on_board(player: Player) -> QuerySet[BirdRoost]:
    """returns all roosts on the board"""
    return BirdRoost.objects.filter(player=player, building_slot__isnull=False)


def roost_at_clearing_number(player: Player, clearing_number: int) -> BirdRoost:
    """returns the roost at the given clearing number,
    raises value error if no roost at that clearing number"""
    try:
        roost = BirdRoost.objects.get(
            player=player, building_slot__clearing__clearing_number=clearing_number
        )
    except BirdRoost.DoesNotExist as e:
        raise ValueError({"detail": str(e)})
    return roost
