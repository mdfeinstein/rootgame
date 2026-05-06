from typing import Union
from django.db import transaction

from game.models.game_models import Player, HandEntry
from game.models.moles.turn import MoleTurn, MoleBirdsong, MoleDaylight, MoleEvening
from game.queries.moles.turn import get_phase
from game.utility.textchoice import next_choice
from game.transactions.general import next_players_turn
from game.transactions.moles.birdsong import place_burrow_warriors


@transaction.atomic
def next_step(player: Player):
    """
    moves to next step in the current phase or next phase, launching events if necessary
    e.g.: for card effects that need to be triggered at a specific step
    """
    phase = get_phase(player)
    match phase:
        case MoleBirdsong():
            phase.step = next_choice(MoleBirdsong.MoleBirdsongSteps, phase.step)
        case MoleDaylight():
            phase.step = next_choice(MoleDaylight.MoleDaylightSteps, phase.step)
        case MoleEvening():
            phase.step = next_choice(MoleEvening.MoleEveningSteps, phase.step)
        case _:
            raise ValueError("Invalid phase")
    phase.save()

    step_effect(player, phase)


@transaction.atomic
def create_moles_turn(player: Player):
    # create turn
    turn = MoleTurn.create_turn(player)

    from game.serializers.logs.general import log_turn

    log_turn(player.game, player, turn_number=turn.turn_number + 1)


@transaction.atomic
def step_effect(
    player: Player, phase: Union[MoleBirdsong, MoleDaylight, MoleEvening, None] = None
):
    """executes any 'passive' effects that should occur at a specific step
    ex: drawing or launching events
    typically called from next_step
    """
    if phase is None:
        phase = get_phase(player)

    from game.transactions.crafted_cards.saboteurs import saboteurs_check
    from game.transactions.crafted_cards.eyrie_emigre import is_emigre
    from game.transactions.crafted_cards.charm_offensive import check_charm_offensive

    match phase:
        case MoleBirdsong():
            match phase.step:
                case MoleBirdsong.MoleBirdsongSteps.NOT_STARTED:
                    from game.serializers.logs.general import (
                        get_or_log_phase,
                        get_current_turn_log,
                    )

                    get_or_log_phase(
                        player.game,
                        player,
                        "Birdsong",
                        parent=get_current_turn_log(player.game, player),
                    )
                    if not saboteurs_check(player):
                        next_step(player)
                case MoleBirdsong.MoleBirdsongSteps.PLACE_WARRIORS:
                    place_burrow_warriors(player)
                case MoleBirdsong.MoleBirdsongSteps.BEFORE_END:
                    if not is_emigre(player):
                        next_step(player)
                case MoleBirdsong.MoleBirdsongSteps.COMPLETED:
                    step_effect(player)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for Moles Birdsong: {phase.step}"
                    )
        case MoleDaylight():
            match phase.step:
                case MoleDaylight.MoleDaylightSteps.NOT_STARTED:
                    from game.serializers.logs.general import (
                        get_or_log_phase,
                        get_current_turn_log,
                    )

                    get_or_log_phase(
                        player.game,
                        player,
                        "Daylight",
                        parent=get_current_turn_log(player.game, player),
                    )
                    next_step(player)
                case MoleDaylight.MoleDaylightSteps.ACTIONS:
                    pass
                case MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS:
                    pass
                case MoleDaylight.MoleDaylightSteps.SWAY_MINISTER:
                    pass
                case MoleDaylight.MoleDaylightSteps.BEFORE_END:
                    next_step(player)
                case MoleDaylight.MoleDaylightSteps.COMPLETED:
                    step_effect(player)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for Moles Daylight: {phase.step}"
                    )
        case MoleEvening():
            match phase.step:
                case MoleEvening.MoleEveningSteps.NOT_STARTED:
                    from game.serializers.logs.general import (
                        get_or_log_phase,
                        get_current_turn_log,
                    )

                    get_or_log_phase(
                        player.game,
                        player,
                        "Evening",
                        parent=get_current_turn_log(player.game, player),
                    )
                    if not check_charm_offensive(player):
                        next_step(player)
                case MoleEvening.MoleEveningSteps.PROCESS_REVEALED_CARDS:
                    from game.transactions.moles.evening import process_revealed_cards
                    process_revealed_cards(player)
                case MoleEvening.MoleEveningSteps.CRAFT:
                    pass
                case MoleEvening.MoleEveningSteps.DRAW:
                    from game.transactions.moles.evening import draw_cards
                    draw_cards(player)
                case MoleEvening.MoleEveningSteps.DISCARD:
                    hand_size = HandEntry.objects.filter(player=player).count()
                    if hand_size <= 5:
                        next_step(player)
                case MoleEvening.MoleEveningSteps.BEFORE_END:
                    next_step(player)
                case MoleEvening.MoleEveningSteps.COMPLETED:
                    end_moles_turn(player)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for Moles Evening: {phase.step}"
                    )
        case _:
            raise ValueError("Invalid phase")


@transaction.atomic
def end_moles_turn(player: Player):
    """ends the current turn, generating the next turn and moving to the next players phase"""
    try:
        evening = get_phase(player)
        if not isinstance(evening, MoleEvening):
            raise ValueError("Not Evening phase")
        evening.step = MoleEvening.MoleEveningSteps.COMPLETED
        evening.save()
    except Exception:
        pass
    next_players_turn(player.game)
    reset_moles_turn(player)


@transaction.atomic
def reset_moles_turn(player: Player):
    """resets moles components to initial state
    -- reset ministers 'used' status
    -- reset tunnels crafted_with status
    -- reset citadel and market crafted_with status
    -- reset brigadier action state
    """
    from game.models.moles.ministers import Minister
    from game.models.moles.tokens import Tunnel
    from game.models.moles.buildings import Citadel, Market

    Minister.objects.filter(player=player).update(used=False)
    Citadel.objects.filter(player=player).update(crafted_with=False)
    Market.objects.filter(player=player).update(crafted_with=False)

    # Reset brigadier action state for next turn
    current_turn = MoleTurn.objects.filter(player=player).order_by('-turn_number').first()
    if current_turn:
        MoleDaylight.objects.filter(turn=current_turn).update(
            brigadier_action=MoleDaylight.BrigadierAction.NONE
        )
