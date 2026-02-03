from game.models.cats.tokens import CatWood
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


def count_wood_tokens_in_supply(player: Player) -> int:
    """returns the number of wood tokens in reserve"""
    return CatWood.objects.filter(player=player, clearing__isnull=True).count()


def get_unused_sawmills(player: Player) -> QuerySet[Sawmill]:
    """returns a list of player's unused sawmills"""
    return Sawmill.objects.filter(
        player=player, used=False, building_slot__isnull=False
    )
