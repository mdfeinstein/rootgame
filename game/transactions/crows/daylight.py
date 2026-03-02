from game.queries.crows.turn import get_phase
from django.db import transaction
from game.models.game_models import Player
from game.models.crows.turn import CrowTurn, CrowDaylight
from .actions import crows_plot, crows_move, crows_battle, crows_trick

@transaction.atomic
def do_daylight_action(player: Player, action_type: str, **kwargs):
    """
    Executes a daylight action for the Crows and decrements remaining actions.
    """
    daylight = get_phase(player)
    if not isinstance(daylight, CrowDaylight):
        raise ValueError("Not in Crow's Daylight phase")
    if daylight.step != CrowDaylight.CrowDaylightSteps.ACTIONS:
        raise ValueError("Not in Actions step")
    if daylight.actions_remaining <= 0:
        raise ValueError("No actions remaining in Daylight")

    if action_type == "plot":
        crows_plot(player, kwargs["clearing"], kwargs["plot_type"], daylight=daylight)
    elif action_type == "move":
        crows_move(player, kwargs["origin"], kwargs["destination"], kwargs["count"])
    elif action_type == "battle":
        crows_battle(player, kwargs["defender_faction"], kwargs["clearing"])
    elif action_type == "trick":
        crows_trick(player, kwargs["plot1"], kwargs["plot2"])
    else:
        raise ValueError(f"Invalid action type: {action_type}")
    
    daylight.actions_remaining -= 1
    daylight.save()

@transaction.atomic
def end_daylight_action_step(player: Player):
    """Advances from Actions to Completed in Daylight"""
    turn = CrowTurn.objects.filter(player=player).last()
    daylight = turn.daylight.first()
    
    if daylight.step != CrowDaylight.CrowDaylightSteps.ACTIONS:
        raise ValueError("Not in Actions step")
        
    # Trigger next step in turn
    from game.transactions.crows.turn import next_step
    next_step(player)
