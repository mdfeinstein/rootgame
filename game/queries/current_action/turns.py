from django.urls import reverse
from game.models.game_models import CraftedCardEntry, Faction, Game, Player
from game.models.events.event import Event, EventType
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.wa.turn import WABirdsong, WADaylight, WAEvening
from game.queries.current_action.events import get_current_event_action
from game.queries.general import get_current_player
from game.queries.cats.turn import get_phase as get_cat_phase
from game.queries.birds.turn import get_phase as get_birds_phase
from game.queries.wa.turn import get_phase as get_wa_phase
from game.models.cats.turn import CatBirdsong, CatDaylight, CatEvening
from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening


def get_current_turn_action(game: Game) -> str | None:
    """Return the current turn action route for the game.
    Returns None if the next set of actions should be examined.
    Raises if there is an inconsistency"""
    # 1. Check for existing event
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
    match phase.step:
        case CatEvening.CatEveningSteps.DRAWING:
            return reverse("cats-evening-draw-cards")
        case CatEvening.CatEveningSteps.DISCARDING:
            return reverse("cats-evening-discard-cards")
        case _:
            raise ValueError("Invalid cats evening step")


def get_birds_birdsong_turn_action(phase: BirdBirdsong):
    match phase.step:
        case BirdBirdsong.BirdBirdsongSteps.EMERGENCY_DRAWING:
            return reverse("birds-emergency-draw")
        case BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE:
            return reverse("birds-add-to-decree")
        case BirdBirdsong.BirdBirdsongSteps.EMERGENCY_ROOSTING:
            return reverse("birds-emergency-roosting")
        case _:
            raise ValueError("Invalid birds birdsong step")


def get_birds_daylight_turn_action(phase: BirdDaylight):
    match phase.step:
        case BirdDaylight.BirdDaylightSteps.CRAFTING:
            return reverse("birds-craft")
        case BirdDaylight.BirdDaylightSteps.RECRUITING:
            return reverse("birds-recruit")
        case BirdDaylight.BirdDaylightSteps.MOVING:
            return reverse("birds-move")
        case BirdDaylight.BirdDaylightSteps.BATTLING:
            return reverse("birds-battle")
        case BirdDaylight.BirdDaylightSteps.BUILDING:
            return reverse("birds-build")
        case _:
            raise ValueError("Invalid birds daylight step")


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
    phase = get_wa_phase(player)
    match phase:
        case WABirdsong():
            return get_wa_birdsong_turn_action(phase)
        case WADaylight():
            return get_wa_daylight_turn_action(phase)
        case WAEvening():
            return get_wa_evening_turn_action(phase)
        case _:
            raise ValueError("Invalid wa phase")


def get_wa_birdsong_turn_action(phase: WABirdsong):
    match phase.step:
        case WABirdsong.WABirdsongSteps.REVOLT:
            return reverse("wa-revolt")
        case WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY:
            return reverse("wa-spread-sympathy")
        case _:
            raise ValueError("Invalid Woodland Alliance birdsong step")


def get_wa_daylight_turn_action(phase: WADaylight):
    match phase.step:
        case WADaylight.WADaylightSteps.ACTIONS:
            return reverse("wa-daylight")
        case _:
            raise ValueError("Invalid Woodland Alliance daylight step")


def get_wa_evening_turn_action(phase: WAEvening):
    match phase.step:
        case WAEvening.WAEveningSteps.MILITARY_OPERATIONS:
            return reverse("wa-operations")
        case WAEvening.WAEveningSteps.DISCARDING:
            return reverse("wa-discard-cards")
        case _:
            raise ValueError("Invalid Woodland Alliance evening step")
