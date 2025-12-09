from game.models.cats.buildings import Sawmill
from game.models.game_models import Game, Player, Suit
from django.db.models import QuerySet


def get_unused_sawmill_by_clearing_number(
    player: Player, clearing_number: int
) -> Sawmill | None:
    """returns an unused sawmill at the given clearing number"""
    sawmill = Sawmill.objects.filter(player=player, used=False).first()
    return sawmill


def get_sawmills_by_suit(player: Player, suit: Suit) -> QuerySet[Sawmill]:
    """returns a list of player's sawmills of the given suit"""
    if suit == Suit.WILD:
        return Sawmill.objects.filter(player=player, building_slot__isnull=False)
    else:
        return Sawmill.objects.filter(
            player=player,
            building_slot__isnull=False,
            building_slot__clearing__suit=suit,
        )
