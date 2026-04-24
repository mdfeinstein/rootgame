from django.db import transaction

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.buildings import BirdRoost
from game.models.birds.turn import BirdBirdsong
from game.models.game_models import Clearing, Player
from game.queries.birds.roosts import get_roosts_on_board
from game.queries.birds.turn import get_phase, validate_phase, validate_step
from game.queries.general import get_player_hand_size, validate_player_has_card_in_hand
from game.transactions.general import draw_card_from_deck_to_hand, place_piece_from_supply_into_clearing, place_warriors_into_clearing
from game.models.birds.player import DecreeEntry


@transaction.atomic
def emergency_draw(player: Player):
    """
    If bird player has no cards in hand, draws a card from the deck.
    if not, do nothing.
    either way, move onto the next step.
    """
    from game.transactions.birds.turn import next_step

    # check right timing
    birdsong = validate_phase(player, BirdBirdsong)
    validate_step(player, BirdBirdsong.BirdBirdsongSteps.EMERGENCY_DRAWING)
    # check if player has cards in hand and draw if not
    if get_player_hand_size(player) == 0:
        hand_entry = draw_card_from_deck_to_hand(player)
        from game.serializers.logs.general import log_draw, get_current_phase_log
        log_draw(player.game, player, [hand_entry.card], parent=get_current_phase_log(player.game, player))
    # move to next step
    next_step(player)


@transaction.atomic
def add_card_to_decree(player: Player, card: CardsEP, column: DecreeEntry.Column):
    """adds the given card to the player's Decree"""
    from game.transactions.birds.turn import next_step
    from game.models.game_models import Suit

    birdsong = get_phase(player)
    assert type(birdsong) == BirdBirdsong
    # validate timing
    validate_step(player, BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE)
    # validate player has card in hand
    card_in_hand = validate_player_has_card_in_hand(player, card)
    # validate that two cards have not yet been placed in decree
    if birdsong.cards_added_to_decree > 2:
        raise ValueError("More than two cards already added to decree! Critical Error")
    elif birdsong.cards_added_to_decree == 2:
        raise ValueError(
            "Two cards already added to decree. We should have already moved to next step"
        )

    # check if bird card. if so, check that we haven't already added a bird card to decree
    if card.value.suit == Suit.WILD:
        if birdsong.bird_card_added_to_decree:
            raise ValueError("Bird card already added to decree")
        # set flag
        birdsong.bird_card_added_to_decree = True
    # add card to decree from hand
    decree_entry = DecreeEntry.objects.create(
        player=player,
        column=column,
        card=card_in_hand.card,
    )
    # remove card from player's hand
    card_model = card_in_hand.card
    card_in_hand.delete()
    # increment cards added and flag bird card added if needed
    birdsong.cards_added_to_decree += 1

    from game.serializers.logs.birds import log_birds_add_to_decree
    from game.serializers.logs.general import get_current_phase_log
    log_birds_add_to_decree(player.game, player, decree_entry, parent=get_current_phase_log(player.game, player))
    # move to next step if all cards have been added
    birdsong.save()
    if birdsong.cards_added_to_decree == 2:
        end_add_to_decree_step(player)


@transaction.atomic
def end_add_to_decree_step(player: Player):
    """ends the current add to decree step,
    verifying that atleast one card has been added"""
    from game.transactions.birds.turn import next_step

    birdsong = get_phase(player)
    assert type(birdsong) == BirdBirdsong
    # validate timing
    validate_step(player, BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE)
    # validate that all cards have been added
    if birdsong.cards_added_to_decree == 0:
        raise ValueError("Must add at least one card to decree")
    # move to next step
    next_step(player)


@transaction.atomic
def place_roost(player: Player, clearing: Clearing):
    """places a roost on the board in the given clearing"""
    if player.game != clearing.game:
        raise ValueError("Player is not in the same game as the clearing")
    roost = BirdRoost.objects.filter(player=player, building_slot__isnull=True).first()
    if roost is None:
        raise ValueError("No roost on the board")
    # place roost
    place_piece_from_supply_into_clearing(roost, clearing)


@transaction.atomic
def try_auto_emergency_roost(player: Player):
    """
    Tries to automate the emergency roost step.
    If player does not need to emergency roost (has at least one roost on board),
    then moves to next step.
    If player does need to emergency roost and there is only one option,
    then automatically places the roost on the board.
    Otherwise, does nothing.
    """
    from game.transactions.birds.turn import next_step
    from game.models.game_models import Warrior

    birdsong = get_phase(player)
    assert type(birdsong) == BirdBirdsong, "Not BirdBirdsong phase"
    assert (
        birdsong.step == BirdBirdsong.BirdBirdsongSteps.EMERGENCY_ROOSTING
    ), "Not Emergency Roosting step"
    # if player has a roost on the board, move to next step
    if get_roosts_on_board(player).exists():
        next_step(player)
        return
    # see if there is one clearing with least warriors
    clearings_in_game = list(Clearing.objects.filter(game=player.game))
    # first pass: get the lowest warrior count
    lowest_warrior_count = None
    for clearing_ in clearings_in_game:
        if lowest_warrior_count is None:
            lowest_warrior_count = Warrior.objects.filter(clearing=clearing_).count()
        else:
            lowest_warrior_count = min(
                lowest_warrior_count, Warrior.objects.filter(clearing=clearing_).count()
            )
    # second pass: find the clearing with the least warriros
    clearing_with_lowest_warriors = None
    for clearing_ in clearings_in_game:
        warrior_count = Warrior.objects.filter(clearing=clearing_).count()
        if warrior_count == lowest_warrior_count:
            if clearing_with_lowest_warriors is None:
                clearing_with_lowest_warriors = clearing_
            else:  # at least two clearings have the same lowest warrior count
                return  # do nothing, player needs to choose
    assert (
        clearing_with_lowest_warriors is not None
    ), "No clearing with lowest warrior count found, this should never happen"
    # if we are here, then we have a unique clearing with the lowest warrior count
    emergency_roost(player, clearing_with_lowest_warriors)


@transaction.atomic
def emergency_roost(player: Player, clearing: Clearing):
    """If no roost is on the board, places a roost and 3 warriors on the board
    in the clearing with the fewest total warriors.
    Player chooses if there are multiple clearings.
    This function validates that the player has no roost and that the
    chosen clearing is among those with the fewest total warriors.
    """
    from game.transactions.birds.turn import next_step
    from game.models.game_models import Warrior

    # validate timing
    validate_step(player, BirdBirdsong.BirdBirdsongSteps.EMERGENCY_ROOSTING)
    # validate that player has no roost on board
    if get_roosts_on_board(player).exists():
        raise ValueError("Player has a roost on the board")
    # validate clearing in game
    if clearing.game != player.game:
        raise ValueError("Clearing is not in the same game as player")
    # validate that the chosen clearing is among those with the fewest total warriors
    clearings_in_game = list(Clearing.objects.filter(game=player.game))
    lowest_warrior_count = None
    for clearing_ in clearings_in_game:
        if lowest_warrior_count is None:
            lowest_warrior_count = Warrior.objects.filter(clearing=clearing_).count()
        else:
            lowest_warrior_count = min(
                lowest_warrior_count, Warrior.objects.filter(clearing=clearing_).count()
            )
    if Warrior.objects.filter(clearing=clearing).count() != lowest_warrior_count:
        raise ValueError(
            "Chosen clearing does not have the fewest total warriors. "
            + f"lowest warrior count: {lowest_warrior_count}. "
            + f"Chosen clearing has {Warrior.objects.filter(clearing=clearing).count()}"
        )
    # place roost and warriors
    place_roost(player, clearing)
    place_warriors_into_clearing(player, clearing, 3)

    from game.serializers.logs.birds import log_birds_emergency_roost
    from game.serializers.logs.general import get_current_phase_log
    log_birds_emergency_roost(player.game, player, clearing.clearing_number, parent=get_current_phase_log(player.game, player))

    # move to next step
    birdsong = get_phase(player)
    assert type(birdsong) == BirdBirdsong
    next_step(player)
