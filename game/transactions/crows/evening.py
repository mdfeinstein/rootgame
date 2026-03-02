from django.db import transaction
from game.models.game_models import Player, Faction
from game.models.crows.turn import CrowTurn, CrowEvening
from game.models.crows.tokens import PlotToken
from game.queries.general import validate_player_has_card_in_hand, get_player_hand_size
from game.queries.crows.turn import validate_step, get_phase
from game.transactions.general import discard_card_from_hand
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.crows.turn import next_step
from .actions import crows_plot, crows_move, crows_battle, crows_trick

@transaction.atomic
def do_exert_action(player: Player, action_type: str, **kwargs):
    """
    Executes an exert action for the Crows and marks exert as used.
    Advances step to DRAWING immediately after action.
    """
    evening = get_phase(player)
    if not isinstance(evening, CrowEvening):
        raise ValueError("Not in Crow's Evening phase")
    if evening.step != CrowEvening.CrowEveningSteps.EXERT:
        raise ValueError("Not in Exert step")
        
    if evening.exert_used:
        raise ValueError("Exert already used this turn")

    if action_type == "plot":
        crows_plot(player, kwargs["clearing"], kwargs["plot_type"])
    elif action_type == "move":
        crows_move(player, kwargs["origin"], kwargs["destination"], kwargs["count"])
    elif action_type == "battle":
        crows_battle(player, kwargs["defender_faction"], kwargs["clearing"])
    elif action_type == "trick":
        crows_trick(player, kwargs["plot1"], kwargs["plot2"])
    else:
        raise ValueError(f"Invalid action type: {action_type}")
    
    evening.exert_used = True
    evening.save()
    # Move to next step
    next_step(player)

@transaction.atomic
def calculate_crow_draw_amount(player: Player) -> int:
    """Calculates how many cards the Crows draw. Base 1 + 1 for each face-up extortion token."""
    face_up_extortion = PlotToken.objects.filter(
        player=player, 
        plot_type=PlotToken.PlotType.EXTORTION, 
        is_facedown=False,
        clearing__isnull=False
    ).count()
    return 1 + face_up_extortion

@transaction.atomic
def check_discard_step(player: Player):
    """Moves to next step if player has 5 or fewer cards"""
    validate_step(player, CrowEvening.CrowEveningSteps.DISCARDING)
    evening = get_phase(player)
    if not isinstance(evening, CrowEvening):
        raise ValueError("Not in Crow's Evening phase")
        
    if get_player_hand_size(player) <= 5:
        next_step(player)

@transaction.atomic
def discard_card(player: Player, card: CardsEP):
    """Discard a card from the player's hand, moving to next step if they are down to 5 cards"""
    validate_step(player, CrowEvening.CrowEveningSteps.DISCARDING)
    evening = get_phase(player)
    if not isinstance(evening, CrowEvening):
        raise ValueError("Not in Crow's Evening phase")
        
    if get_player_hand_size(player) <= 5:
        raise ValueError("Player must have more than 5 cards to discard")
        
    card_in_hand = validate_player_has_card_in_hand(player, card)
    if player.faction != Faction.CROWS.value:
        raise ValueError("Player is not crows")
        
    # discard card
    discard_card_from_hand(player, card_in_hand)
    
    # move to next step if player has 5 or fewer cards
    if get_player_hand_size(player) <= 5:
        next_step(player)
