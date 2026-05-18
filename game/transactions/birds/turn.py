from typing import Union
from django.db import transaction

from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening, BirdTurn
from game.models.birds.player import BirdLeader, DecreeEntry, Vizier
from game.models.birds.buildings import BirdRoost
from game.models.game_models import Faction, Player
from game.queries.birds.turn import get_phase, get_turmoil_event, validate_phase, validate_step
from game.transactions.crafted_cards.saboteurs import saboteurs_check
from game.transactions.crafted_cards.eyrie_emigre import is_emigre
from game.transactions.crafted_cards.charm_offensive import check_charm_offensive
from game.transactions.crafted_cards.informants import informants_check
from game.transactions.general import next_players_turn
from game.utility.textchoice import next_choice


@transaction.atomic
def create_birds_turn(player: Player):
    # create turn
    turn = BirdTurn.create_turn(player)

    from game.serializers.logs.general import log_turn
    log_turn(player.game, player, turn_number=turn.turn_number + 1)
    # Birdsong log will be created in BirdBirdsong.NOT_STARTED step_effect


@transaction.atomic
def end_birds_turn(player: Player):
    """ends the current turn, generating the next turn and moving to the next players phase
    careful where this is called. will move evening to completed if called.
    """
    assert player.faction == Faction.BIRDS.value
    phase = get_phase(player)
    assert type(phase) == BirdEvening
    assert phase.step == BirdEvening.BirdEveningSteps.COMPLETED
    next_players_turn(player.game)
    reset_birds_turn(player)


@transaction.atomic
def reset_birds_turn(player: Player):
    """resets birds turn to initial state
    -- reset roosts crafted_with status
    -- reset decrees and viziers
    """
    # reset roosts
    BirdRoost.objects.filter(player=player).update(crafted_with=False)
    # reset decrees
    DecreeEntry.objects.filter(player=player).update(fulfilled=False)
    # reset viziers
    Vizier.objects.filter(player=player).update(fulfilled=False)


@transaction.atomic
def next_step(player: Player):
    phase = get_phase(player)
    match phase:
        case BirdBirdsong():
            phase.step = next_choice(BirdBirdsong.BirdBirdsongSteps, phase.step)
        case BirdDaylight():
            phase.step = next_choice(BirdDaylight.BirdDaylightSteps, phase.step)
        case BirdEvening():
            phase.step = next_choice(BirdEvening.BirdEveningSteps, phase.step)
        case _:
            raise ValueError("Invalid phase")
    phase.save()
    step_effect(player, phase)


@transaction.atomic
def step_effect(
    player: Player, phase: Union[BirdBirdsong, BirdDaylight, BirdEvening, None] = None
):
    if phase is None:
        phase = get_phase(player)

    # Import action functions here to avoid circular imports
    from game.transactions.birds.birdsong import emergency_draw, try_auto_emergency_roost
    from game.transactions.birds.daylight import (
        recruit_turmoil_check, move_turmoil_check, battle_turmoil_check, build_turmoil_check
    )
    from game.transactions.birds.evening import roost_scoring, draw_cards, check_discard_step
    from game.transactions.birds.turmoil import turmoil

    match phase:
        case BirdBirdsong():
            match phase.step:
                case BirdBirdsong.BirdBirdsongSteps.NOT_STARTED:
                    from game.serializers.logs.general import get_or_log_phase, get_current_turn_log
                    get_or_log_phase(
                        player.game,
                        player,
                        "Birdsong",
                        parent=get_current_turn_log(player.game, player),
                    )
                    if not saboteurs_check(player):
                        next_step(player)
                case BirdBirdsong.BirdBirdsongSteps.EMERGENCY_DRAWING:
                    from game.queries.crafted_cards import get_coffin_makers_player
                    from game.transactions.crafted_cards.coffin_makers import (
                        score_coffins,
                        release_warriors,
                    )

                    coffin_player = get_coffin_makers_player(player.game)
                    if coffin_player == player:
                        score_coffins(player)
                        release_warriors(player.game)

                    emergency_draw(player)

                case BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE:
                    pass
                case BirdBirdsong.BirdBirdsongSteps.EMERGENCY_ROOSTING:
                    try_auto_emergency_roost(player)
                case BirdBirdsong.BirdBirdsongSteps.BEFORE_END:
                    if not is_emigre(player):
                        next_step(player)
                case BirdBirdsong.BirdBirdsongSteps.COMPLETED:
                    step_effect(player)
        case BirdDaylight():
            match phase.step:
                case BirdDaylight.BirdDaylightSteps.NOT_STARTED:
                    from game.serializers.logs.general import get_or_log_phase, get_current_turn_log
                    get_or_log_phase(
                        player.game,
                        player,
                        "Daylight",
                        parent=get_current_turn_log(player.game, player),
                    )
                    next_step(player)
                case BirdDaylight.BirdDaylightSteps.CRAFTING:
                    pass
                case BirdDaylight.BirdDaylightSteps.RECRUITING:
                    recruit_turmoil_check(player)
                case BirdDaylight.BirdDaylightSteps.MOVING:
                    move_turmoil_check(player)
                case BirdDaylight.BirdDaylightSteps.BATTLING:
                    battle_turmoil_check(player)
                case BirdDaylight.BirdDaylightSteps.BUILDING:
                    build_turmoil_check(player)
                case BirdDaylight.BirdDaylightSteps.BEFORE_END:
                    next_step(player)
                case BirdDaylight.BirdDaylightSteps.COMPLETED:
                    step_effect(player)
        case BirdEvening():
            match phase.step:
                case BirdEvening.BirdEveningSteps.NOT_STARTED:
                    from game.serializers.logs.general import get_or_log_phase, get_current_turn_log
                    get_or_log_phase(
                        player.game,
                        player,
                        "Evening",
                        parent=get_current_turn_log(player.game, player),
                    )
                    if not check_charm_offensive(player):
                        next_step(player)
                case BirdEvening.BirdEveningSteps.SCORING:
                    roost_scoring(player)
                case BirdEvening.BirdEveningSteps.DRAWING:
                    is_informants = informants_check(player)
                    if not is_informants:
                        draw_cards(player)
                case BirdEvening.BirdEveningSteps.DISCARDING:
                    check_discard_step(player)
                case BirdEvening.BirdEveningSteps.BEFORE_END:
                    next_step(player)
                case BirdEvening.BirdEveningSteps.COMPLETED:
                    end_birds_turn(player)
        case _:
            raise ValueError("Invalid phase")
