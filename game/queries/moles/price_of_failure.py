from game.models.game_models import Player
from game.models.moles.ministers import Minister
from game.errors import IllegalActionError


def get_highest_rank_swayed_ministers(player: Player) -> list[Minister]:
    """Get all swayed ministers of the highest rank.

    Rank order: LORD > NOBLE > SQUIRE
    Returns list of Minister objects all of the same (highest) rank.
    """
    swayed = Minister.objects.filter(player=player, swayed=True)
    if not swayed.exists():
        return []

    # group by tier, starting from highest. return first non-empty tier
    lords = [
        minister
        for minister in swayed
        if minister.crown_type == Minister.MinisterRank.LORD
    ]
    if len(lords) > 0:
        return lords
    nobles = [
        minister
        for minister in swayed
        if minister.crown_type == Minister.MinisterRank.NOBLE
    ]
    if len(nobles) > 0:
        return nobles
    squires = [
        minister
        for minister in swayed
        if minister.crown_type == Minister.MinisterRank.SQUIRE
    ]
    if len(squires) > 0:
        return squires
    # jsut to satisfy type checker...
    return []


def validate_minister_is_highest_rank(
    player: Player, minister_name: Minister.MinisterName
):
    """Validate that the given minister is swayed and of the highest rank.

    Raises IllegalActionError if minister is not of highest rank.
    """
    highest_rank_ministers = get_highest_rank_swayed_ministers(player)
    highest_rank_names = [m.name for m in highest_rank_ministers]

    if minister_name not in highest_rank_names:
        raise IllegalActionError(
            f"Minister {minister_name} is not of the highest available rank"
        )
