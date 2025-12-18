from game.models.birds.player import BirdLeader
from game.models.game_models import Player


def get_available_leaders(player: Player) -> list[BirdLeader]:
    """returns a list of available leaders for the given player"""
    return list(BirdLeader.objects.filter(player=player, available=True))


def get_leader_from_enum(player: Player, leader: BirdLeader.BirdLeaders) -> BirdLeader:
    """returns the leader with the given leader enum"""
    return BirdLeader.objects.get(player=player, leader=leader)
