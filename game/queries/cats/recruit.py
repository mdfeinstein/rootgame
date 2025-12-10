from game.models.cats.buildings import Recruiter
from game.models.cats.turn import CatDaylight
from game.models.game_models import Clearing, Player, Warrior
from game.queries.cats.turn import get_phase
from django.db.models import QuerySet


def is_recruit_used(player: Player) -> bool:
    """returns True if player has used recruiter action this turn, since it can only be used once"""
    phase = get_phase(player)
    if type(phase) != CatDaylight:
        raise ValueError("Not Daylight phase, this query shouldn't be called")
    return phase.recruit_used


def troops_in_reserve(player: Player) -> int:
    """returns the number of troops in reserve"""
    return Warrior.objects.filter(player=player, clearing=None).count()


def unused_recruiters(player: Player):
    """returns the unused recruiters on the board"""
    return Recruiter.objects.filter(
        player=player, used=False, building_slot__isnull=False
    )


def unused_recruiters_by_clearing(
    player: Player, clearing: Clearing, count: int | None = None
):
    """returns the unused recruiters on the given clearing.
    if count is provided, returns only that many, and raises if not enough recruiters"""
    if count is None:
        return unused_recruiters(player).filter(building_slot__clearing=clearing)
    else:
        recruiters = unused_recruiters(player).filter(building_slot__clearing=clearing)[
            :count
        ]
        if len(recruiters) < count:
            raise ValueError(
                f"count provided ({count}) is more than the recruiters in clearing ({len(recruiters)})"
            )
        return recruiters


def is_enough_reserve(player: Player) -> bool:
    """returns True if there are enough warriors in reserve to use all recruiters"""
    recruiters = unused_recruiters(player)
    return recruiters.count() <= troops_in_reserve(player)
