from django.urls import reverse
from game.models.birds.setup import BirdsSimpleSetup
from game.models.cats.setup import CatsSimpleSetup
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import Faction, Game, Player


def get_setup_action(game: Game) -> str | None:
    """Return the current setup action route for the game.
    Returns None if the next set of actions should be examined.
    Raises if there is an inconsistency in the setup status
    """
    setup = GameSimpleSetup.objects.get(game=game)
    match setup.status:
        case GameSimpleSetup.GameSetupStatus.CATS_SETUP:
            return get_cats_setup_action(game)
        case GameSimpleSetup.GameSetupStatus.BIRDS_SETUP:
            return get_birds_setup_action(game)
        case GameSimpleSetup.GameSetupStatus.ALL_SETUP_COMPLETED:
            return None
        case _:
            raise ValueError("Invalid setup status")


def get_cats_setup_action(game: Game) -> str | None:
    """Return the current cats setup action route for the game or raises if unexpected step"""
    cat_player = Player.objects.get(game=game, faction=Faction.CATS)
    cats_setup = CatsSimpleSetup.objects.get(player=cat_player)
    match cats_setup.step:
        case CatsSimpleSetup.Steps.PICKING_CORNER:
            return reverse("cats-setup-pick-corner")
        case CatsSimpleSetup.Steps.PLACING_BUILDINGS:
            return reverse("cats-setup-place-initial-building")
        case CatsSimpleSetup.Steps.PENDING_CONFIRMATION:
            return reverse("cats-setup-confirm-completed-setup")
        case _:
            raise ValueError("Invalid cats setup step")


def get_birds_setup_action(game: Game) -> str | None:
    """Return the current birds setup action route for the game or raises if unexpected step"""
    bird_player = Player.objects.get(game=game, faction=Faction.BIRDS)
    birds_setup = BirdsSimpleSetup.objects.get(player=bird_player)
    match birds_setup.step:
        case BirdsSimpleSetup.Steps.PICKING_CORNER:
            return reverse("birds-setup-pick-corner")
        case BirdsSimpleSetup.Steps.CHOOSING_LEADER:
            return reverse("birds-setup-choose-leader")
        case BirdsSimpleSetup.Steps.PENDING_CONFIRMATION:
            return reverse("birds-setup-confirm-completed-setup")
        case _:
            raise ValueError("Invalid birds setup step")
