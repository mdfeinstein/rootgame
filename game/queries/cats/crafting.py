from game.models.cats.buildings import Workshop
from game.models.game_models import Player


def get_unused_workshop_by_clearing_number(
    player: Player,
    clearing_number: int,
) -> Workshop | None:
    """returns an unused sawmill at the given clearing number"""
    workshop = Workshop.objects.filter(player=player, used=False).first()
    return workshop


def validate_unused_workshops_by_clearing_number(
    player: Player, clearing_number: int, count: int
):
    """raises if not enough unused workshops at the given clearing number"""
    workshop_count = Workshop.objects.filter(player=player, used=False).count()
    if workshop_count < count:
        raise ValueError("Not enough unused workshops at that clearing")
