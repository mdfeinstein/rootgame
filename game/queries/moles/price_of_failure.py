from game.models.moles.ministers import Minister
from game.errors import IllegalActionError


def get_highest_rank_swayed_ministers(player):
    """Get all swayed ministers of the highest rank.

    Rank order: LORD > NOBLE > SQUIRE
    Returns list of Minister objects all of the same (highest) rank.
    """
    swayed = Minister.objects.filter(player=player, swayed=True)
    if not swayed.exists():
        return []

    # Group by rank
    lord_count = sum(1 for m in swayed if m.crown_type == Minister.MinisterRank.LORD)
    noble_count = sum(1 for m in swayed if m.crown_type == Minister.MinisterRank.NOBLE)
    squire_count = sum(1 for m in swayed if m.crown_type == Minister.MinisterRank.SQUIRE)

    if lord_count > 0:
        return [m for m in swayed if m.crown_type == Minister.MinisterRank.LORD]
    elif noble_count > 0:
        return [m for m in swayed if m.crown_type == Minister.MinisterRank.NOBLE]
    else:
        return [m for m in swayed if m.crown_type == Minister.MinisterRank.SQUIRE]


def validate_minister_is_highest_rank(player, minister_name):
    """Validate that the given minister is swayed and of the highest rank.

    Raises IllegalActionError if minister is not of highest rank.
    """
    highest_rank_ministers = get_highest_rank_swayed_ministers(player)
    highest_rank_names = [m.name for m in highest_rank_ministers]

    if minister_name not in highest_rank_names:
        raise IllegalActionError(
            f"Minister {minister_name} is not of the highest available rank"
        )
