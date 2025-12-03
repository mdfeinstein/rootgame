from game.models.cats.turn import CatBirdsong, CatDaylight, CatEvening, CatTurn
from game.models.game_models import Player


def get_phase(player: Player) -> CatBirdsong | CatDaylight | CatEvening:
    """returns the current phase of the turn"""
    # get most recent turn
    cat_turn = CatTurn.objects.filter(player=player).order_by("-turn_number").first()
    if cat_turn is None:
        raise ValueError("No turns found")
    # get phase
    if cat_turn.birdsong.step != CatBirdsong.CatBirdsongSteps.COMPLETED:
        return cat_turn.birdsong
    elif cat_turn.daylight.step != CatDaylight.CatDaylightSteps.COMPLETED:
        return cat_turn.daylight
    elif cat_turn.evening.step != CatEvening.CatEveningSteps.COMPLETED:
        return cat_turn.evening
    else:
        raise ValueError("All phases of this turn completed")


def get_actions_remaining(player: Player) -> int:
    """returns the number of actions remaining in the daylight action phase"""
    cat_turn = CatTurn.objects.filter(player=player).order_by("-turn_number").first()
    if cat_turn is None:
        raise ValueError("No turns found")
    return CatDaylight.objects.get(turn=cat_turn).actions_left
