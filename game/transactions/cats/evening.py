from django.db import transaction

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.cats.buildings import CatBuildingTypes
from game.models.game_models import Faction, Player
from game.queries.cats.building import buildings_on_board
from game.queries.cats.turn import get_phase
from game.queries.general import get_current_player, get_player_hand_size, validate_player_has_card_in_hand
from game.transactions.general import draw_card_from_deck_to_hand, discard_card_from_hand


@transaction.atomic
def cat_evening_draw(player: Player):
    """draws cards from the deck and adds it to the cat player's hand
    number of cards depends on recruiters on the board
    """
    from game.models.cats.turn import CatEvening

    if player.faction != Faction.CATS:
        raise ValueError("Not a cats player")
    if get_current_player(player.game) != player:
        raise ValueError("Not this player's turn")

    evening = get_phase(player)
    if type(evening) != CatEvening:
        raise ValueError("Not Evening phase")
    if evening.step != CatEvening.CatEveningSteps.DRAWING:
        raise ValueError("Not Drawing step")

    cards_drawn_by_recruiters_on_board = [1, 1, 1, 2, 2, 3, 3]
    recruiter_count = buildings_on_board(player, CatBuildingTypes.RECRUITER)
    cards_to_draw = cards_drawn_by_recruiters_on_board[recruiter_count]

    drawn_cards = []
    for _ in range(cards_to_draw):
        entry = draw_card_from_deck_to_hand(player)
        drawn_cards.append(entry.card)

    from game.serializers.logs.general import log_draw, get_current_phase_log

    log_draw(
        player.game,
        player,
        drawn_cards,
        parent=get_current_phase_log(player.game, player),
    )

    from game.transactions.cats.turn import next_step
    next_step(player)


@transaction.atomic
def cat_discard_card(player: Player, card: CardsEP):
    from game.models.cats.turn import CatEvening

    evening = get_phase(player)
    if type(evening) != CatEvening:
        raise ValueError("Not Evening phase")
    if evening.step != CatEvening.CatEveningSteps.DISCARDING:
        raise ValueError("Not discarding step")

    hand_entry = validate_player_has_card_in_hand(player, card)
    card_model = hand_entry.card
    discard_card_from_hand(player, hand_entry)

    from game.serializers.logs.general import log_discard, get_current_phase_log

    log_discard(
        player.game,
        player,
        card_model,
        parent=get_current_phase_log(player.game, player),
    )

    check_auto_discard(player)


@transaction.atomic
def check_auto_discard(player: Player):
    if get_player_hand_size(player) <= 5:
        from game.transactions.cats.turn import next_step
        next_step(player)
