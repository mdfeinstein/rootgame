from typing import Union
from django.db import transaction

from game.models.game_models import Player, Faction
from game.models.cats.turn import CatBirdsong, CatDaylight, CatEvening, CatTurn
from game.queries.cats.turn import get_phase
from game.transactions.general import next_players_turn
from game.utility.textchoice import next_choice


@transaction.atomic
def create_cats_turn(player: Player):
    turn = CatTurn.create_turn(player)

    from game.serializers.logs.general import log_turn
    log_turn(player.game, player, turn_number=turn.turn_number + 1)


@transaction.atomic
def cat_end_turn(player: Player):
    """ends the current turn, generating the next turn and moving to the next players phase"""
    try:
        evening = get_phase(player)
        if type(evening) != CatEvening:
            raise ValueError("Not Evening phase")
        evening.step = CatEvening.CatEveningSteps.COMPLETED
        evening.save()
    except ValueError:
        pass
    reset_cats_turn(player)
    next_players_turn(player.game)


@transaction.atomic
def reset_cats_turn(player: Player):
    """resets cats turn to initial state
    -- reset workshops crafted_with status
    -- reset recruiter stations used status
    -- reset sawmills used status
    """
    from game.models.cats.buildings import Workshop, Recruiter, Sawmill

    Workshop.objects.filter(player=player).update(crafted_with=False)
    Recruiter.objects.filter(player=player).update(used=False)
    Sawmill.objects.filter(player=player).update(used=False)


@transaction.atomic
def next_step(player: Player):
    phase = get_phase(player)
    match phase:
        case CatBirdsong():
            phase.step = next_choice(CatBirdsong.CatBirdsongSteps, phase.step)
        case CatDaylight():
            phase.step = next_choice(CatDaylight.CatDaylightSteps, phase.step)
        case CatEvening():
            phase.step = next_choice(CatEvening.CatEveningSteps, phase.step)
    phase.save()
    step_effect(player, phase)


@transaction.atomic
def step_effect(
    player: Player, phase: Union[CatBirdsong, CatDaylight, CatEvening, None] = None
):
    if phase is None:
        phase = get_phase(player)

    from game.transactions.crafted_cards.saboteurs import saboteurs_check
    from game.transactions.crafted_cards.eyrie_emigre import is_emigre
    from game.transactions.crafted_cards.charm_offensive import check_charm_offensive
    from game.transactions.crafted_cards.informants import informants_check
    from game.transactions.cats.birdsong import check_auto_place_wood
    from game.transactions.cats.evening import cat_evening_draw, check_auto_discard

    match phase:
        case CatBirdsong():
            match phase.step:
                case CatBirdsong.CatBirdsongSteps.NOT_STARTED:
                    from game.serializers.logs.general import get_or_log_phase, get_current_turn_log
                    get_or_log_phase(
                        player.game,
                        player,
                        "Birdsong",
                        parent=get_current_turn_log(player.game, player),
                    )
                    if not saboteurs_check(player):
                        next_step(player)
                case CatBirdsong.CatBirdsongSteps.PLACING_WOOD:
                    from game.queries.crafted_cards import get_coffin_makers_player
                    from game.transactions.crafted_cards.coffin_makers import (
                        score_coffins,
                        release_warriors,
                    )

                    coffin_player = get_coffin_makers_player(player.game)
                    if coffin_player == player:
                        score_coffins(player)
                        release_warriors(player.game)

                    check_auto_place_wood(player)
                case CatBirdsong.CatBirdsongSteps.BEFORE_END:
                    if not is_emigre(player):
                        next_step(player)
                case CatBirdsong.CatBirdsongSteps.COMPLETED:
                    step_effect(player)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for Cats Birdsong: {phase.step}"
                    )
        case CatDaylight():
            match phase.step:
                case CatDaylight.CatDaylightSteps.NOT_STARTED:
                    from game.serializers.logs.general import get_or_log_phase, get_current_turn_log
                    get_or_log_phase(
                        player.game,
                        player,
                        "Daylight",
                        parent=get_current_turn_log(player.game, player),
                    )
                    next_step(player)
                case CatDaylight.CatDaylightSteps.CRAFTING:
                    pass
                case CatDaylight.CatDaylightSteps.ACTIONS:
                    pass
                case CatDaylight.CatDaylightSteps.BEFORE_END:
                    next_step(player)
                case CatDaylight.CatDaylightSteps.COMPLETED:
                    step_effect(player)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for Cats Daylight: {phase.step}"
                    )
        case CatEvening():
            match phase.step:
                case CatEvening.CatEveningSteps.NOT_STARTED:
                    from game.serializers.logs.general import get_or_log_phase, get_current_turn_log
                    get_or_log_phase(
                        player.game,
                        player,
                        "Evening",
                        parent=get_current_turn_log(player.game, player),
                    )
                    if not check_charm_offensive(player):
                        next_step(player)
                case CatEvening.CatEveningSteps.DRAWING:
                    is_informants = informants_check(player)
                    if not is_informants:
                        cat_evening_draw(player)
                case CatEvening.CatEveningSteps.DISCARDING:
                    check_auto_discard(player)
                case CatEvening.CatEveningSteps.BEFORE_END:
                    next_step(player)
                case CatEvening.CatEveningSteps.COMPLETED:
                    cat_end_turn(player)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for Cats Evening: {phase.step}"
                    )
        case _:
            raise ValueError("Invalid phase")
