from typing import Union
from django.db import transaction

from game.models.game_models import Player
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowTurn, CrowBirdsong, CrowDaylight, CrowEvening
from game.queries.crows.turn import get_phase
from game.utility.textchoice import next_choice
from game.transactions.general import draw_card_from_deck_to_hand, next_players_turn


@transaction.atomic
def next_step(player: Player):
    """
    moves to next step in the current phase or next phase, launching events if necessary
    e.g.: for card effects that need to be triggered at a specific step
    """
    phase = get_phase(player)
    match phase:
        case CrowBirdsong():
            phase.step = next_choice(CrowBirdsong.CrowBirdsongSteps, phase.step)
        case CrowDaylight():
            phase.step = next_choice(CrowDaylight.CrowDaylightSteps, phase.step)
        case CrowEvening():
            phase.step = next_choice(CrowEvening.CrowEveningSteps, phase.step)
        case _:
            raise ValueError("Invalid phase")
    phase.save()
    step_effect(player, phase)


@transaction.atomic
def step_effect(
    player: Player, phase: Union[CrowBirdsong, CrowDaylight, CrowEvening, None] = None
):
    """executes any 'passive' effects that should occur at a specific step
    ex: drawing or launching events
    typically called from next_step
    """
    if phase is None:
        phase = get_phase(player)
    
    match phase:
        case CrowBirdsong():
            match phase.step:
                case CrowBirdsong.CrowBirdsongSteps.NOT_STARTED:
                    pass
                case CrowBirdsong.CrowBirdsongSteps.CRAFT:
                    from game.queries.crafted_cards import get_coffin_makers_player
                    from game.transactions.crafted_cards.coffin_makers import score_coffins, release_warriors
                    from game.transactions.crafted_cards.saboteurs import saboteurs_check
                    
                    coffin_player = get_coffin_makers_player(player.game)
                    if coffin_player == player:
                        score_coffins(player)
                        release_warriors(player.game)
                        
                    saboteurs_check(player)
                case CrowBirdsong.CrowBirdsongSteps.FLIP:
                    pass
                case CrowBirdsong.CrowBirdsongSteps.RECRUIT:
                    pass
                case CrowBirdsong.CrowBirdsongSteps.COMPLETED:
                    from game.transactions.crafted_cards.eyrie_emigre import is_emigre
                    if not is_emigre(player):
                        step_effect(player, None)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for Crows Birdsong: {phase.step.name}"
                    )
        case CrowDaylight():
            match phase.step:
                case CrowDaylight.CrowDaylightSteps.ACTIONS:
                    pass
                case CrowDaylight.CrowDaylightSteps.COMPLETED:
                    from game.transactions.crafted_cards.charm_offensive import check_charm_offensive
                    if not check_charm_offensive(player):
                        step_effect(player, None)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for Crows Daylight: {phase.step.name}"
                    )
        case CrowEvening():
            match phase.step:
                case CrowEvening.CrowEveningSteps.EXERT:
                    pass
                case CrowEvening.CrowEveningSteps.DRAWING:
                    from game.transactions.crafted_cards.informants import informants_check
                    is_informants = informants_check(player)
                    if not is_informants:
                        if phase.exert_used:
                            next_step(player)
                        else:
                            from game.transactions.crows.evening import calculate_crow_draw_amount
                            amount = calculate_crow_draw_amount(player)
                            for _ in range(amount):
                                draw_card_from_deck_to_hand(player)
                            phase.cards_drawn = amount
                            phase.save()
                            next_step(player)
                case CrowEvening.CrowEveningSteps.DISCARDING:
                    from game.transactions.crows.evening import check_discard_step
                    check_discard_step(player)
                case CrowEvening.CrowEveningSteps.COMPLETED:
                    end_crows_turn(player)
                case _:
                    raise ValueError(f"Invalid step in step_effect for Crows Evening: {phase.step.name}")
        case _:
            raise ValueError("Invalid phase")

@transaction.atomic
def end_crows_turn(player: Player):
    """ends the current turn, generating the next turn and moving to the next players phase"""
    try:
        evening = get_phase(player)
        if not isinstance(evening, CrowEvening):
            raise ValueError("Not Evening phase")
        evening.step = CrowEvening.CrowEveningSteps.COMPLETED
        evening.save()
    except Exception:
        pass
    CrowTurn.create_turn(player)
    next_players_turn(player.game)
    reset_crows_turn(player)

@transaction.atomic
def reset_crows_turn(player: Player):
    """resets crows components to initial state"""
    PlotToken.objects.filter(player=player).update(crafted_with=False)
