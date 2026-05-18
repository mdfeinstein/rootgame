from typing import Union
from django.db import transaction

from game.models.game_models import Player
from game.models.wa.turn import WABirdsong, WADaylight, WAEvening, WATurn
from game.models.wa.player import OfficerEntry
from game.models.wa.tokens import WASympathy
from game.queries.wa.turn import get_phase
from game.transactions.general import next_players_turn
from game.utility.textchoice import next_choice


@transaction.atomic
def create_wa_turn(player: Player):
    turn = WATurn.create_turn(player)

    from game.serializers.logs.general import log_turn
    log_turn(player.game, player, turn_number=turn.turn_number + 1)


@transaction.atomic
def end_turn(player: Player):
    """ends the current turn, generating the next turn and moving to the next players phase"""
    try:
        evening = get_phase(player)
        if not isinstance(evening, WAEvening):
            raise ValueError("Not Evening phase")
        evening.step = WAEvening.WAEveningSteps.COMPLETED
        evening.save()
    except:
        pass
    next_players_turn(player.game)
    reset_wa_turn(player)


@transaction.atomic
def reset_wa_turn(player: Player):
    """resets wa components to initial state
    -- reset crafting pieces (sympathy)
    -- reset officers 'used' status
    """
    WASympathy.objects.filter(player=player).update(crafted_with=False)
    OfficerEntry.objects.filter(player=player).update(used=False)


@transaction.atomic
def next_step(player: Player):
    """moves to next step in the current phase or next phase, launching events if necessary"""
    phase = get_phase(player)
    match phase:
        case WABirdsong():
            phase.step = next_choice(WABirdsong.WABirdsongSteps, phase.step)
        case WADaylight():
            phase.step = next_choice(WADaylight.WADaylightSteps, phase.step)
        case WAEvening():
            phase.step = next_choice(WAEvening.WAEveningSteps, phase.step)
        case _:
            raise ValueError("Invalid phase")
    phase.save()
    step_effect(player, phase)


@transaction.atomic
def step_effect(
    player: Player, phase: Union[WABirdsong, WADaylight, WAEvening, None] = None
):
    """executes any 'passive' effects that should occur at a specific step"""
    if phase is None:
        phase = get_phase(player)

    from game.transactions.crafted_cards.saboteurs import saboteurs_check
    from game.transactions.crafted_cards.eyrie_emigre import is_emigre
    from game.transactions.crafted_cards.charm_offensive import check_charm_offensive
    from game.transactions.crafted_cards.informants import informants_check
    from game.transactions.wa.evening import draw_cards, check_discard_step

    match phase:
        case WABirdsong():
            match phase.step:
                case WABirdsong.WABirdsongSteps.NOT_STARTED:
                    from game.serializers.logs.general import get_or_log_phase, get_current_turn_log
                    get_or_log_phase(
                        player.game,
                        player,
                        "Birdsong",
                        parent=get_current_turn_log(player.game, player),
                    )
                    if not saboteurs_check(player):
                        next_step(player)
                case WABirdsong.WABirdsongSteps.REVOLT:
                    from game.queries.crafted_cards import get_coffin_makers_player
                    from game.transactions.crafted_cards.coffin_makers import (
                        score_coffins,
                        release_warriors,
                    )

                    coffin_player = get_coffin_makers_player(player.game)
                    if coffin_player == player:
                        score_coffins(player)
                        release_warriors(player.game)
                case WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY:
                    pass
                case WABirdsong.WABirdsongSteps.BEFORE_END:
                    if not is_emigre(player):
                        next_step(player)
                case WABirdsong.WABirdsongSteps.COMPLETED:
                    step_effect(player)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for WA Birdsong: {phase.step.name}"
                    )
        case WADaylight():
            match phase.step:
                case WADaylight.WADaylightSteps.NOT_STARTED:
                    from game.serializers.logs.general import get_or_log_phase, get_current_turn_log
                    get_or_log_phase(
                        player.game,
                        player,
                        "Daylight",
                        parent=get_current_turn_log(player.game, player),
                    )
                    next_step(player)
                case WADaylight.WADaylightSteps.ACTIONS:
                    pass
                case WADaylight.WADaylightSteps.BEFORE_END:
                    next_step(player)
                case WADaylight.WADaylightSteps.COMPLETED:
                    step_effect(player)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for WA Daylight: {phase.step.name}"
                    )
        case WAEvening():
            match phase.step:
                case WAEvening.WAEveningSteps.NOT_STARTED:
                    from game.serializers.logs.general import get_or_log_phase, get_current_turn_log
                    get_or_log_phase(
                        player.game,
                        player,
                        "Evening",
                        parent=get_current_turn_log(player.game, player),
                    )
                    if not check_charm_offensive(player):
                        next_step(player)
                case WAEvening.WAEveningSteps.MILITARY_OPERATIONS:
                    pass
                case WAEvening.WAEveningSteps.DRAWING:
                    is_informants = informants_check(player)
                    if not is_informants:
                        draw_cards(player)
                case WAEvening.WAEveningSteps.DISCARDING:
                    check_discard_step(player)
                case WAEvening.WAEveningSteps.BEFORE_END:
                    next_step(player)
                case WAEvening.WAEveningSteps.COMPLETED:
                    end_turn(player)
                case _:
                    raise ValueError(f"Invalid step in step_effect: {phase.step.name}")
        case _:
            raise ValueError("Invalid phase")
