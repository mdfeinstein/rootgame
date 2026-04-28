from django.db import transaction

from game.models.birds.turn import BirdEvening
from game.models.game_models import Player
from game.queries.birds.roosts import get_roosts_on_board
from game.queries.birds.turn import validate_step, get_phase
from game.queries.general import get_player_hand_size, validate_player_has_card_in_hand
from game.transactions.general import (
    draw_card_from_deck_to_hand,
    discard_card_from_hand,
)
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Faction
from game.errors import UnavailableActionError, IllegalActionError, InternalGameError


@transaction.atomic
def roost_scoring(player: Player):
    """scoring for roosts"""
    validate_step(player, BirdEvening.BirdEveningSteps.SCORING)
    evening = get_phase(player)
    assert type(evening) == BirdEvening
    scoring_per_roost_on_board = [
        0,
        0,
        1,
        2,
        3,
        4,
        4,
        5,
    ]
    roosts_on_board = len(get_roosts_on_board(player))
    from game.transactions.general import raise_score

    raise_score(player, scoring_per_roost_on_board[roosts_on_board])

    if scoring_per_roost_on_board[roosts_on_board] > 0:
        from game.serializers.logs.birds import log_birds_score_roosts
        from game.serializers.logs.general import get_current_phase_log

        log_birds_score_roosts(
            player.game,
            player,
            scoring_per_roost_on_board[roosts_on_board],
            parent=get_current_phase_log(player.game, player),
        )

    from game.transactions.birds.turn import next_step

    next_step(player)


@transaction.atomic
def draw_cards(player: Player):
    """draws cards for the player during evening drawing step"""
    validate_step(player, BirdEvening.BirdEveningSteps.DRAWING)
    evening = get_phase(player)
    assert type(evening) == BirdEvening
    drawing_per_roost_on_board = [1, 1, 1, 2, 2, 2, 3, 3]
    roosts_on_board = len(get_roosts_on_board(player))
    drawn_cards_objs = []
    for _ in range(drawing_per_roost_on_board[roosts_on_board]):
        drawn_cards_objs.append(draw_card_from_deck_to_hand(player).card)

    from game.serializers.logs.general import log_draw, get_current_phase_log

    log_draw(
        player.game,
        player,
        drawn_cards_objs,
        parent=get_current_phase_log(player.game, player),
    )

    from game.transactions.birds.turn import next_step

    next_step(player)


@transaction.atomic
def check_discard_step(player: Player):
    """moves to next step if player has 5 or fewer cards"""
    validate_step(player, BirdEvening.BirdEveningSteps.DISCARDING)
    evening = get_phase(player)
    assert type(evening) == BirdEvening
    if get_player_hand_size(player) <= 5:
        from game.transactions.birds.turn import next_step

        next_step(player)


@transaction.atomic
def discard_card(player: Player, card: CardsEP):
    """discard a card from the player's hand, moving to next step if they are down to 5 cards"""
    validate_step(player, BirdEvening.BirdEveningSteps.DISCARDING)
    evening = get_phase(player)
    assert type(evening) == BirdEvening
    if get_player_hand_size(player) <= 5:
        raise UnavailableActionError("Player must have more than 5 cards to discard")
    card_in_hand = validate_player_has_card_in_hand(player, card)
    if player.faction != Faction.BIRDS.value:
        raise UnavailableActionError("Player is not birds")
    card_model = card_in_hand.card
    discard_card_from_hand(player, card_in_hand)

    from game.serializers.logs.general import log_discard, get_current_phase_log

    log_discard(
        player.game,
        player,
        card_model,
        parent=get_current_phase_log(player.game, player),
    )

    if get_player_hand_size(player) <= 5:
        from game.transactions.birds.turn import next_step

        next_step(player)
