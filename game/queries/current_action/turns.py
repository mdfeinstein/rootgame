from django.urls import reverse
from game.models.game_models import Faction, Game, Player
from game.queries.current_action.events import get_current_event_action
from game.queries.general import get_current_player
from game.queries.cats.turn import get_phase as get_cat_phase
from game.queries.birds.turn import get_phase as get_birds_phase
from game.models.cats.turn import CatBirdsong, CatDaylight, CatEvening
from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening


def get_current_turn_action(game: Game) -> str | None:
    """Return the current turn action route for the game.
    Returns None if the next set of actions should be examined.
    Raises if there is an inconsistency"""
    # check for event
    event_action = get_current_event_action(game)
    if event_action is not None:
        return event_action
    player = get_current_player(game)
    match player.faction:
        case Faction.CATS:
            print(f"cats turn!")
            return get_cats_turn_action(player)
        case Faction.BIRDS:
            return get_birds_turn_action(player)
        case Faction.WOODLAND_ALLIANCE:
            return get_wa_turn_action(player)
        case _:
            raise ValueError("Invalid faction")


def get_cats_turn_action(player: Player) -> str | None:
    """Return the current cats turn action route for the player or raises if unexpected step"""
    phase = get_cat_phase(player)
    match phase:
        case CatBirdsong():
            print(f"cats birdsong!")
            return get_cats_birdsong_turn_action(phase)
        case CatDaylight():
            return get_cats_daylight_turn_action(phase)
        case CatEvening():
            return get_cats_evening_turn_action(phase)
        case _:
            raise ValueError("Invalid cats phase")


def get_cats_birdsong_turn_action(phase: CatBirdsong):
    match phase.step:
        case CatBirdsong.CatBirdsongSteps.PLACING_WOOD:
            print(f"cats birdsong place wood!")
            return reverse("cats-birdsong-place-wood")
        case _:
            raise ValueError("Invalid cats birdsong step")


def get_cats_daylight_turn_action(phase: CatDaylight):
    match phase.step:
        case CatDaylight.CatDaylightSteps.CRAFTING:
            return reverse("cats-daylight-craft")
        case CatDaylight.CatDaylightSteps.ACTIONS:
            return reverse("cats-daylight-actions")
        case _:
            raise ValueError("Invalid cats daylight step")


def get_cats_evening_turn_action(phase: CatEvening):
    raise ValueError("Not yet implemented")


def get_birds_birdsong_turn_action(phase: BirdBirdsong):
    raise ValueError("Not yet implemented")


def get_birds_daylight_turn_action(phase: BirdDaylight):
    raise ValueError("Not yet implemented")
    pass


def get_birds_evening_turn_action(phase: BirdEvening):
    raise ValueError("Not yet implemented")


def get_birds_turn_action(player: Player) -> str | None:
    """Return the current birds turn action route for the player or raises if unexpected step"""
    phase = get_birds_phase(player)
    match phase:
        case BirdBirdsong():
            return get_birds_birdsong_turn_action(phase)
        case BirdDaylight():
            return get_birds_daylight_turn_action(phase)
        case BirdEvening():
            return get_birds_evening_turn_action(phase)
        case _:
            raise ValueError("Invalid birds phase")


def get_wa_turn_action(player: Player) -> str | None:
    """Return the current wa turn action route for the player or raises if unexpected step"""
    raise ValueError("Not yet implemented")
