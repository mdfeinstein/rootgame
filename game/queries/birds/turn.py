from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening, BirdTurn
from game.models.game_models import Player


def get_phase(player: Player) -> BirdBirdsong | BirdDaylight | BirdEvening:
    """returns the current phase of the turn"""
    # get most recent turn
    bird_turn = BirdTurn.objects.filter(player=player).order_by("-turn_number").first()
    if bird_turn is None:
        raise ValueError("No turns found")
    # get phase
    if bird_turn.birdsong.step != BirdBirdsong.BirdBirdsongSteps.COMPLETED:
        return bird_turn.birdsong
    elif bird_turn.daylight.step != BirdDaylight.BirdDaylightSteps.COMPLETED:
        return bird_turn.daylight
    elif bird_turn.evening.step != BirdEvening.BirdEveningSteps.COMPLETED:
        return bird_turn.evening
    else:
        raise ValueError("All phases of this turn completed")
