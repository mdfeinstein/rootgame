from game.queries.crows.turn import validate_turn
from game.queries.crows.turn import get_phase
from django.db import transaction
from game.models.game_models import Clearing, Player, Warrior, Token
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowDaylight
from game.transactions.general import (
    move_warriors,
    place_piece_from_supply_into_clearing,
)
from game.transactions.battle import start_battle
from game.transactions.removal import player_removes_warriors
from game.queries.general import warrior_count_in_clearing

@transaction.atomic
def crows_plot(player: Player, clearing: Clearing, plot_type: str, daylight: CrowDaylight = None):
    """
    Crows Plot action:
    - Removes Crow warriors equal to plots_placed + 1 in clearing.
    - Places the specified PlotToken face down.
    """
    turn = validate_turn(player)
    if daylight is None:
        daylight = CrowDaylight.objects.get(turn=turn)
    plots_placed = daylight.plots_placed
    print(f"plots_placed: {plots_placed}")
    cost = plots_placed + 1
    
    # Validation: Clearing empty of plots
    if PlotToken.objects.filter(clearing=clearing).exists():
        raise ValueError("Clearing already has a plot token")
    
    # Validation: Enough warriors
    if warrior_count_in_clearing(player, clearing) < cost:
        raise ValueError(f"Not enough warriors in clearing to place a plot. Cost: {cost}")
    
    # Validation: Token available in supply
    plot_token = PlotToken.objects.filter(player=player, clearing__isnull=True, plot_type=plot_type).first()
    if not plot_token:
        raise ValueError(f"No plot token of type {plot_type} available in supply")
    
    from game.serializers.logs.general import get_current_phase_log
    from game.serializers.logs.crows import log_crows_plot
    parent = log_crows_plot(
        player.game, 
        player, 
        clearing.clearing_number, 
        plot_type,
        parent=get_current_phase_log(player.game, player)
    )

    # Effect: Remove warriors
    # Using attacker=player, defender=player as a workaround or just direct removal
    # The spec says "remove crow warriors", usually implies returning to supply
    player_removes_warriors(clearing, None, player, cost, parent=parent) # None as 'remover' might be okay or just use someone else
    
    # Effect: Place plot token facedown
    plot_token.is_facedown = True
    place_piece_from_supply_into_clearing(plot_token, clearing)
    
    # Update count on the object instance to maintain consistency in transactions
    daylight.plots_placed += 1
    daylight.save()


@transaction.atomic
def crows_move(player: Player, origin: Clearing, destination: Clearing, count: int):
    """Crows Move: ignore rule (handled by general move update)"""
    move_warriors(player, origin, destination, count, ignore_rule=True)

    from game.serializers.logs.general import log_move, get_current_phase_log
    log_move(
        player.game, 
        player, 
        origin.clearing_number, 
        destination.clearing_number, 
        count,
        parent=get_current_phase_log(player.game, player)
    )

@transaction.atomic
def crows_battle(player: Player, defender_faction: str, clearing: Clearing):
    """Crows Battle"""
    battle = start_battle(player.game, player.faction, defender_faction, clearing)

    from game.transactions.battle import log_battle_start
    from game.serializers.logs.general import get_current_phase_log
    log_battle_start(
        battle, 
        player, 
        parent=get_current_phase_log(player.game, player)
    )

@transaction.atomic
def crows_trick(player: Player, plot1: PlotToken, plot2: PlotToken):
    """
    Crows Trick:
    - Swaps the clearings of two plot tokens.
    - Both must be on board and in the same is_facedown state.
    """
    if not plot1.clearing or not plot2.clearing:
        raise ValueError("Both plot tokens must be on the board")
    
    if plot1.is_facedown != plot2.is_facedown:
        raise ValueError("Both plot tokens must be in the same state (both facedown or both faceup)")
    
    if plot1.player != player or plot2.player != player:
        raise ValueError("You can only trick your own plot tokens")

    # Swap clearings
    c1 = plot1.clearing
    c2 = plot2.clearing
    
    plot1.clearing = None # temp
    plot1.save()
    
    plot2.clearing = c1
    plot2.save()
    
    plot1.clearing = c2
    plot1.save()

    from game.serializers.logs.general import get_current_phase_log
    from game.serializers.logs.crows import log_crows_trick
    log_crows_trick(
        player.game, 
        player, 
        c1.clearing_number, 
        c2.clearing_number,
        parent=get_current_phase_log(player.game, player)
    )
