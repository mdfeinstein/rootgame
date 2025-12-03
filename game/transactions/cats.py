from django.db import transaction
from game.models.cats.buildings import Sawmill
from game.models.cats.tokens import CatWood
from game.models.cats.turn import CatBirdsong, CatTurn
from game.models.game_models import Player
from game.queries.cats.turn import get_phase
from game.utility.textchoice import next_choice


@transaction.atomic
def produce_wood(player: Player, sawmill: Sawmill):
    """not to be used for overwork. use for birdsong"""
    # check that sawmill is not used
    if sawmill.building_slot is None:
        raise ValueError("Sawmill is not placed")
    if sawmill.used:
        raise ValueError("Sawmill is already used")
    # check that sawmill is player's
    if sawmill.player != player:
        raise ValueError("Sawmill is not owned by player")
    # get a supply wood token to place
    wood_token = CatWood.objects.filter(player=player, clearing=None).first()
    if wood_token is None:
        raise ValueError("No wood tokens left to place")
    # assign wood token to sawmill clearing

    wood_token.clearing = sawmill.building_slot.clearing
    wood_token.save()
    sawmill.used = True
    sawmill.save()
    # check if all sawmills have been used
    print(
        Sawmill.objects.filter(player=player, used=False, building_slot__isnull=False)
    )
    if not Sawmill.objects.filter(
        player=player, used=False, building_slot__isnull=False
    ).exists():
        print("all sawmills used")
        # move to next part of phase
        phase = get_phase(player)
        if type(phase) == CatBirdsong:
            phase.step = next_choice(CatBirdsong.CatBirdsongSteps, phase.step)
            print(phase.step)
            phase.save()

        else:
            raise ValueError(
                f"Wrong phase type, should be CatBirdsong, got {type(phase)}"
            )


@transaction.atomic
def create_cats_turn(player: Player):
    # create turn
    turn = CatTurn.create_turn(player)
