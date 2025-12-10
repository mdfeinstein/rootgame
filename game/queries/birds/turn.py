from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening, BirdTurn
from game.models.game_models import Player


def get_phase(player: Player) -> BirdBirdsong | BirdDaylight | BirdEvening:
    """returns the current phase of the turn"""
    # get most recent turn
    bird_turn = BirdTurn.objects.filter(player=player).order_by("-turn_number").first()
    if bird_turn is None:
        raise ValueError("No turns found")
    # get phase
    birdsong = BirdBirdsong.objects.get(turn=bird_turn)
    daylight = BirdDaylight.objects.get(turn=bird_turn)
    evening = BirdEvening.objects.get(turn=bird_turn)
    if birdsong.step != BirdBirdsong.BirdBirdsongSteps.COMPLETED:
        return birdsong
    elif daylight.step != BirdDaylight.BirdDaylightSteps.COMPLETED:
        return daylight
    elif evening.step != BirdEvening.BirdEveningSteps.COMPLETED:
        return evening
    else:
        raise ValueError("All phases of this turn completed")
