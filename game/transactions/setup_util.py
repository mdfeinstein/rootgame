from game.models.events.setup import GameSimpleSetup
from game.models.game_models import Game
from django.db import transaction

from game.utility.textchoice import next_choice


@transaction.atomic
def next_player_setup(game: Game):
    """moves along the setup process, and if complete, starts the game"""
    simple_setup = GameSimpleSetup.objects.get(game=game)
    simple_setup.status = next_choice(
        GameSimpleSetup.GameSetupStatus, simple_setup.status
    )
    simple_setup.save()
    if simple_setup.status == GameSimpleSetup.GameSetupStatus.ALL_SETUP_COMPLETED:
        game.status = Game.GameStatus.SETUP_COMPLETED
        game.save()
