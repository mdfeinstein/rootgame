from django.db import transaction

from game.models.cats.buildings import Sawmill
from game.models.cats.tokens import CatWood
from game.models.game_models import Player
from game.queries.cats.wood import (
    count_wood_tokens_in_supply,
    get_unused_sawmills,
)
from game.transactions.general import place_piece_from_supply_into_clearing
from game.errors import UnavailableActionError, IllegalActionError, InternalGameError


@transaction.atomic
def produce_wood(player: Player, sawmill: Sawmill):
    """not to be used for overwork. use for birdsong"""
    if sawmill.building_slot is None:
        raise IllegalActionError("Sawmill is not placed")
    if sawmill.used:
        raise IllegalActionError("Sawmill is already used")
    if sawmill.player != player:
        raise IllegalActionError("Sawmill is not owned by player")

    wood_token = CatWood.objects.filter(player=player, clearing=None).first()
    if wood_token is None:
        raise UnavailableActionError("No wood tokens left to place")

    place_piece_from_supply_into_clearing(wood_token, sawmill.building_slot.clearing)
    sawmill.used = True
    sawmill.save()

    from game.serializers.logs.cats import log_cats_wood_placement
    from game.serializers.logs.general import get_current_phase_log

    log_cats_wood_placement(
        player.game,
        player,
        sawmill.building_slot.clearing.clearing_number,
        1,
        parent=get_current_phase_log(player.game, player),
    )

    if not Sawmill.objects.filter(
        player=player, used=False, building_slot__isnull=False
    ).exists():
        from game.transactions.cats.turn import next_step

        next_step(player)


@transaction.atomic
def cat_produce_all_wood(player: Player):
    """produces wood at all available sawmills"""
    sawmills = get_unused_sawmills(player)
    for sawmill in sawmills:
        produce_wood(player, sawmill)


@transaction.atomic
def check_auto_place_wood(player: Player):
    """checks if player has enough wood tokens to place at sawmills.
    If so, produces wood and moves to next step
    """
    sawmills = get_unused_sawmills(player)
    wood_tokens = count_wood_tokens_in_supply(player)
    if wood_tokens >= sawmills.count():
        cat_produce_all_wood(player)
