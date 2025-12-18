from typing import cast
from django.db import transaction
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.buildings import BirdRoost
from game.models.birds.player import BirdLeader, DecreeEntry, Vizier
from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening
from game.models.events.birds import TurmoilEvent
from game.models.events.event import Event, EventType
from game.models.game_models import (
    Clearing,
    DiscardPileEntry,
    Faction,
    Piece,
    Player,
    Suit,
    Warrior,
)
from game.queries.birds.crafting import (
    get_all_unused_roosts,
    validate_crafting_pieces_satisfy_requirements,
)
from game.queries.birds.roosts import get_roosts_on_board
from game.queries.birds.turn import (
    get_phase,
    get_turmoil_event,
    validate_phase,
    validate_step,
)
from game.queries.general import (
    available_building_slot,
    determine_clearing_rule,
    get_player_hand_size,
    player_has_pieces_in_clearing,
    validate_has_legal_moves,
    validate_player_has_card_in_hand,
    warrior_count_in_supply,
)
from game.transactions.battle import start_battle
from game.transactions.birds_setup import create_birds_turn
from game.transactions.general import (
    craft_card,
    draw_card_from_deck,
    move_warriors,
    next_players_turn,
    place_warriors_into_clearing,
    raise_score,
)
from game.utility.textchoice import next_choice


@transaction.atomic
def emergency_draw(player: Player):
    """
    If bird player has no cards in hand, draws a card from the deck.
    if nto, do nothing.
    eitehr way, move onto the next step.
    """
    # check right timing
    birdsong = validate_phase(player, BirdBirdsong)
    validate_step(player, BirdBirdsong.BirdBirdsongSteps.EMERGENCY_DRAWING)
    # check if player has cards in hand and draw if not
    if get_player_hand_size(player) == 0:
        draw_card_from_deck(player)
    # move to next step
    birdsong.step = next_choice(BirdBirdsong.BirdBirdsongSteps, birdsong.step)
    birdsong.save()


@transaction.atomic
def add_card_to_decree(player: Player, card: CardsEP, column: DecreeEntry.Column):
    """adds the given card to the player's Decree"""
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
        ValueError(
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
    card_in_hand.delete()
    # increment cards addedd and flag bird card added if needed
    birdsong.cards_added_to_decree += 1
    # move to next step if all cards have been added
    birdsong.save()
    if birdsong.cards_added_to_decree == 2:
        end_add_to_decree_step(player)


@transaction.atomic
def end_add_to_decree_step(player: Player):
    """ends the current add to decree step,
    verifying that atleast one card has been added"""
    birdsong = get_phase(player)
    assert type(birdsong) == BirdBirdsong
    # validate timing
    validate_step(player, BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE)
    # validate that all cards have been added
    if birdsong.cards_added_to_decree == 0:
        raise ValueError("Must add at least one card to decree")
    # move to next step
    birdsong.step = next_choice(BirdBirdsong.BirdBirdsongSteps, birdsong.step)
    birdsong.save()
    # check if emergency roost necessary, if it is that step
    if birdsong.step == BirdBirdsong.BirdBirdsongSteps.EMERGENCY_ROOSTING:
        emergency_roost_check(player)


@transaction.atomic
def emergency_roost_check(player: Player):
    """checks if emergency roost step should be skipped"""
    birdsong = get_phase(player)
    assert type(birdsong) == BirdBirdsong, "Not BirdBirdsong phase"
    assert (
        birdsong.step == BirdBirdsong.BirdBirdsongSteps.EMERGENCY_ROOSTING
    ), "Not Emergency Roosting step"
    # check that player has a roost on the board
    if not get_roosts_on_board(player).exists():
        # no roost on board, stay in emergency roosting step
        return
    birdsong.step = next_choice(BirdBirdsong.BirdBirdsongSteps, birdsong.step)
    birdsong.save()


@transaction.atomic
def place_roost(player: Player, clearing: Clearing):
    """places a roost on the board in the given clearing"""
    if player.game != clearing.game:
        raise ValueError("Player is not in the same game as the clearing")
    roost = BirdRoost.objects.filter(player=player, building_slot__isnull=True).first()
    if roost is None:
        raise ValueError("No roost on the board")
    building_slot = available_building_slot(clearing)
    if building_slot is None:
        raise ValueError("No building slot available")
    # check that no other roost in this clearing
    if BirdRoost.objects.filter(
        player=player, building_slot__clearing=clearing
    ).exists():
        raise ValueError("Roost already exists in this clearing")
    # place roost
    roost.building_slot = building_slot
    roost.save()


@transaction.atomic
def emergency_roost(player: Player, clearing: Clearing):
    """If no roost is on the board, places a roost and 3 warriors on the board
    in the clearing with the fewest total warriors.
    Player chooses if there are multiple clearings.
    This function validates that the player has no roost and that the
    chosen clearing is among those with the fewest total warriors.
    """
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
    # move to next step
    birdsong = get_phase(player)
    assert type(birdsong) == BirdBirdsong
    birdsong.step = next_choice(BirdBirdsong.BirdBirdsongSteps, birdsong.step)
    birdsong.save()


def next_daylight_step(player: Player):
    """moves to the next daylight step"""
    daylight = get_phase(player)
    assert type(daylight) == BirdDaylight
    daylight.step = next_choice(BirdDaylight.BirdDaylightSteps, daylight.step)
    daylight.save()
    match daylight.step:
        case BirdDaylight.BirdDaylightSteps.RECRUITING:
            recruit_turmoil_check(player)
        case BirdDaylight.BirdDaylightSteps.MOVING:
            move_turmoil_check(player)
        case BirdDaylight.BirdDaylightSteps.BATTLING:
            battle_turmoil_check(player)
        case BirdDaylight.BirdDaylightSteps.BUILDING:
            build_turmoil_check(player)
        case BirdDaylight.BirdDaylightSteps.COMPLETED:
            begin_evening(player)


@transaction.atomic
def bird_craft_card(player: Player, card: CardsEP, crafting_pieces: list[BirdRoost]):
    """crafts a card with the given pieces. If it is an item, scores the points and discards it
    If not, moves the card to the player's crafted card box.
    raises ValueError if not enough crafting pieces to craft the card or other issues
    """
    validate_step(player, BirdDaylight.BirdDaylightSteps.CRAFTING)
    card_in_hand = validate_player_has_card_in_hand(player, card)
    if not validate_crafting_pieces_satisfy_requirements(player, card, crafting_pieces):
        raise ValueError("Not enough crafting pieces to craft card")
    craft_card(card_in_hand, cast(list[Piece], crafting_pieces))
    # if no more crafting pieces, move to next step
    if get_player_hand_size(player) == 0 or get_all_unused_roosts(player).count() == 0:
        next_daylight_step(player)


@transaction.atomic
def bird_recruit_action(
    player: Player, roost: BirdRoost, decree_entry: DecreeEntry | Vizier
):
    """recruits warriors at the given roost clearing using the decree entry
    raises ValueError if there is an issue
    """
    validate_step(player, BirdDaylight.BirdDaylightSteps.RECRUITING)
    # get clearing, checking that it is on the board
    clearing = roost.building_slot.clearing
    if clearing is None:
        raise ValueError("Roost is not on the board")
    # check that decree_entry is in the correct column and that it has not been used
    if decree_entry.fulfilled:
        raise ValueError("This decree card has already been used")
    if decree_entry.column != DecreeEntry.Column.RECRUIT:
        raise ValueError("Decree card is not in the recruit column")
    # check that the decree suit matches the roost suit
    decree_suit = (
        decree_entry.card.suit if type(decree_entry) == DecreeEntry else Suit.WILD
    )
    if decree_suit != clearing.suit and decree_suit != Suit.WILD:
        raise ValueError("Decree suit does not match roost suit")
    # determine number to recruit, based on leader
    leader = BirdLeader.objects.get(player=player, active=True)
    number_to_recruit = 1
    if leader.leader == BirdLeader.BirdLeaders.CHARISMATIC:
        number_to_recruit = 2
    # check that there are enough warriors in the supply
    if warrior_count_in_supply(player) < number_to_recruit:
        # recruit as many as possible
        place_warriors_into_clearing(player, clearing, warrior_count_in_supply(player))
        # turmoil!
        turmoil(player)
        return
    # recruit warriors
    place_warriors_into_clearing(player, clearing, number_to_recruit)
    # mark decree entry as used
    decree_entry.fulfilled = True
    decree_entry.save()
    # if all decree entries in column are used, move to next step
    if not DecreeEntry.objects.filter(
        player=player, column=decree_entry.column, fulfilled=False
    ).exists():
        next_daylight_step(player)


@transaction.atomic
def bird_move_action(
    player: Player,
    origin_clearing: Clearing,
    target_clearing: Clearing,
    number: int,
    decree_entry: DecreeEntry | Vizier,
):
    """moves warriors from origin_clearing to target_clearing using the decree entry
    raises ValueError if there is an issue
    """
    validate_step(player, BirdDaylight.BirdDaylightSteps.MOVING)
    # check that clearings are in the right game
    if player.game != origin_clearing.game != target_clearing.game:
        raise ValueError("Clearings are not in the same game as each other or player")
    # check that decree_entry is in the correct column and that it has not been used
    if decree_entry.fulfilled:
        raise ValueError("This decree card has already been used")
    if decree_entry.column != DecreeEntry.Column.MOVE:
        raise ValueError("Decree card is not in the move column")
    # check that the decree suit matches the origin clearing suit
    decree_suit = (
        decree_entry.card.suit if type(decree_entry) == DecreeEntry else Suit.WILD
    )
    if decree_suit != origin_clearing.suit and decree_suit != Suit.WILD:
        raise ValueError("Decree suit does not match origin clearing suit")
    # move warriors (movement checks handled in this transaction function)
    move_warriors(player, origin_clearing, target_clearing, number)
    # mark decree entry as used
    decree_entry.fulfilled = True
    decree_entry.save()
    # if all decree entries in column are used, move to next step
    if not DecreeEntry.objects.filter(
        player=player, column=decree_entry.column, fulfilled=False
    ).exists():
        next_daylight_step(player)


@transaction.atomic
def bird_battle_action(
    player: Player,
    defender: Player,
    clearing: Clearing,
    decree_entry: DecreeEntry | Vizier,
):
    """battle the given defender in the given clearing using the decree entry
    raises ValueError if there is an issue
    """
    validate_step(player, BirdDaylight.BirdDaylightSteps.BATTLING)
    # check that the defender is in the same game as the player
    if defender.game != player.game != clearing.game:
        raise ValueError(
            "Defender is not in the same game as the player and the clearing"
        )
    # check decree entry not used and matches clearing
    if decree_entry.fulfilled:
        raise ValueError("This decree card has already been used")
    if decree_entry.column != DecreeEntry.Column.BATTLE:
        raise ValueError("Decree card is not in the battle column")
    decree_suit = (
        decree_entry.card.suit if type(decree_entry) == DecreeEntry else Suit.WILD
    )
    if decree_suit != clearing.suit and decree_suit != Suit.WILD:
        raise ValueError("Decree suit does not match clearing suit")
    # battle checks are in start_battle
    start_battle(player.game, player.faction, defender.faction, clearing)
    # use decree entry
    decree_entry.fulfilled = True
    decree_entry.save()
    # if all decree entries in column are used, move to next step
    if not DecreeEntry.objects.filter(
        player=player, column=decree_entry.column, fulfilled=False
    ).exists():
        next_daylight_step(player)


@transaction.atomic
def bird_build_action(
    player: Player, clearing: Clearing, decree_entry: DecreeEntry | Vizier
):
    """builds a roost in the given clearing using the decree_entry provided"""
    validate_step(player, BirdDaylight.BirdDaylightSteps.BUILDING)
    # check that decree entry is in the correct column and that it has not been used
    if decree_entry.fulfilled:
        raise ValueError("This decree card has already been used")
    if decree_entry.column != DecreeEntry.Column.BUILD:
        raise ValueError("Decree card is not in the build column")
    # check that the decree suit matches the clearing suit
    decree_suit = (
        decree_entry.card.suit if type(decree_entry) == DecreeEntry else Suit.WILD
    )
    if decree_suit != clearing.suit and decree_suit != Suit.WILD:
        raise ValueError("Decree suit does not match clearing suit")
    # check that the clearing is in the right game
    if clearing.game != player.game:
        raise ValueError("Clearing is not in the same game as player")
    # check that player rules this clearing
    if determine_clearing_rule(clearing) != player:
        raise ValueError("Player does not rule this clearing")
    # place roost (which checks fro free building slot and no other roost)
    place_roost(player, clearing)
    # use decree entry
    decree_entry.fulfilled = True
    decree_entry.save()
    # if all decree entries in column are used, move to next step
    if not DecreeEntry.objects.filter(
        player=player, column=DecreeEntry.Column.BUILD, fulfilled=False
    ).exists():
        next_daylight_step(player)


@transaction.atomic
def begin_evening(player: Player):
    """automates scoring and drawing in evening, and discarding too if possible"""
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
    ]  # 0 on board, 1 on board... all 7 on board
    drawing_per_roost_on_board = [1, 1, 1, 2, 2, 2, 3, 3]
    roosts_on_board = len(get_roosts_on_board(player))
    raise_score(player, scoring_per_roost_on_board[roosts_on_board])
    evening.step = next_choice(BirdEvening.BirdEveningSteps, evening.step)
    # draw
    assert evening.step == BirdEvening.BirdEveningSteps.DRAWING
    for _ in range(drawing_per_roost_on_board[roosts_on_board]):
        draw_card_from_deck(player)
    evening.step = next_choice(BirdEvening.BirdEveningSteps, evening.step)
    # ignro discard step, if able
    assert evening.step == BirdEvening.BirdEveningSteps.DISCARDING
    if get_player_hand_size(player) <= 5:
        evening.step = next_choice(BirdEvening.BirdEveningSteps, evening.step)
        evening.save()
        if evening.step == BirdEvening.BirdEveningSteps.COMPLETED:
            end_birds_turn(player)


@transaction.atomic
def end_birds_turn(player: Player):
    """ends the current turn, generating the next turn and moving to the next players phase
    careful where this is called. will move evening to completed if called.
    """
    try:
        evening = get_phase(player)
        if type(evening) != BirdEvening:
            raise ValueError("Not Evening phase")
        evening.step = BirdEvening.BirdEveningSteps.COMPLETED
        evening.save()
    except:
        pass
    create_birds_turn(player)
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
def recruit_turmoil_check(player: Player):
    """
    initiates turmoil if the player can't recruit but needs to,
    either because no warriors in supply or because no matching roosts remaining.
    Also, moves to next step if no recruit decrees present
    """
    recruit_cards = DecreeEntry.objects.filter(
        player=player, column=DecreeEntry.Column.RECRUIT, fulfilled=False
    )
    viziers = Vizier.objects.filter(
        player=player, column=Vizier.Column.RECRUIT, fulfilled=False
    )
    recruit_decrees_remaining = recruit_cards.count() + viziers.count()
    # if no recruit decrees remaining, move to next step
    if recruit_decrees_remaining == 0:
        # move to next step
        next_daylight_step(player)
        return
    # otherwise, do turmoil checks
    if warrior_count_in_supply(player) == 0 and recruit_decrees_remaining != 0:
        turmoil(player)
        return
    # if no remaining recruit decrees are possible, turmoil
    # if wild in recruit (and sitll a roost), then more to do this phase, exit out
    if (
        recruit_cards.filter(card__suit=Suit.WILD).exists()
        or viziers.exists()
        and BirdRoost.objects.filter(player=player, building_slot__isnull=False).count()
        == 0
    ):
        return
    # if no overlap between suits of decrees and roost, turmoil
    recruit_suits = set([decree_entry.card.suit for decree_entry in recruit_cards])
    # no need to add viziers, since they are wild and have already been ruled out
    roost_suits = set(
        [
            roost.building_slot.clearing.suit
            for roost in BirdRoost.objects.filter(
                player=player, building_slot__isnull=False
            )
        ]
    )
    if len(recruit_suits.intersection(roost_suits)) == 0:
        turmoil(player)


@transaction.atomic
def move_turmoil_check(player: Player):
    """
    initiates turmoil if the player can't move but needs to,
    possible reasons:
    -- no warriors present in remaining decree suits
    -- warriors in remaining decree suits can not legally move
    Also, moves to next step if no move decrees present
    """
    move_cards = DecreeEntry.objects.filter(
        player=player, column=DecreeEntry.Column.MOVE, fulfilled=False
    )
    viziers = Vizier.objects.filter(
        player=player, column=Vizier.Column.MOVE, fulfilled=False
    )
    move_decrees_remaining = move_cards.count() + viziers.count()
    if move_decrees_remaining == 0:
        # move to next step
        next_daylight_step(player)
        return
    # otherwise, do turmoil checks
    clearings_with_warriors = {
        warrior.clearing
        for warrior in Warrior.objects.filter(clearing__isnull=False, player=player)
    }
    # check for wilds. if there are, then also check that all warriors are stuck. if not, exit out
    if viziers.exists() or move_cards.filter(card__suit=Suit.WILD).exists():
        # check if warrior groups in each clearing have legal moves
        for clearing in clearings_with_warriors:
            try:
                validate_has_legal_moves(player, clearing)
                # we have something legal to do, exit out
                return
            except ValueError as e:
                pass
        # if we get here, no legal moves. turmoil
        turmoil(player)
        return
    # check remaining decree suits against clearings_with_warriors to see if there are any legal moves
    decree_suits = {decree_entry.card.suit for decree_entry in move_cards}
    for clearing in clearings_with_warriors:
        if clearing.suit not in decree_suits:
            continue
        try:
            validate_has_legal_moves(player, clearing)
            # we have something legal to do, exit out
            return
        except ValueError as e:
            pass
    # if we get here, no legal moves. turmoil
    turmoil(player)
    return


@transaction.atomic
def battle_turmoil_check(player: Player):
    """
    initiates turmoil if the player can't battle but needs to,
    possible reasons:
    -- no warriors present in remaining decree suits
    -- warriors in remaining decree suits have no one to battle
    Also, moves to next step if no battle decrees present
    """
    battle_cards = DecreeEntry.objects.filter(
        player=player, column=DecreeEntry.Column.BATTLE, fulfilled=False
    )
    viziers = Vizier.objects.filter(
        player=player, column=Vizier.Column.BATTLE, fulfilled=False
    )
    battle_decrees_remaining = battle_cards.count() + viziers.count()
    if battle_decrees_remaining == 0:
        # move to next step
        next_daylight_step(player)
        return
    # otherwise, do turmoil checks
    clearings_with_warriors = {
        warrior.clearing
        for warrior in Warrior.objects.filter(clearing__isnull=False, player=player)
    }
    if len(clearings_with_warriors) == 0:
        # cant battle if no warriors anywhere
        turmoil(player)
        return
    # check for wilds. if there are, then also check if warriors have anyone to battle
    if viziers.exists() or battle_cards.filter(card__suit=Suit.WILD).exists():
        # check if warrior groups in each clearing have legal moves
        for clearing in clearings_with_warriors:
            for player_ in Player.objects.filter(game=player.game):
                if player_ == player:
                    continue
                if player_has_pieces_in_clearing(player_, clearing):
                    # we have something legal to do, exit out
                    return

        # if we get here, no legal battles. turmoil
        turmoil(player)
        return
    # check remaining battle suits against clearings_with_warriors to see if there are any legal battles
    battle_suits = {battle_entry.card.suit for battle_entry in battle_cards}
    for clearing in clearings_with_warriors:
        if clearing.suit not in battle_suits:
            continue
        for player_ in Player.objects.filter(game=player.game):
            if player_ == player:
                continue
            if player_has_pieces_in_clearing(player_, clearing):
                # we have something legal to do, exit out
                return


@transaction.atomic
def build_turmoil_check(player: Player):
    """
    initiates turmoil if the player can't build but needs to,
    clearings need to be:
    -- ruled
    -- have no roosts
    -- have a free building slot
    -- match a decree suit
    Also, turmoil if no roosts left in supply
    Also, moves to next step if no build decrees present
    """
    build_cards = DecreeEntry.objects.filter(
        player=player, column=DecreeEntry.Column.BUILD, fulfilled=False
    )
    viziers = Vizier.objects.filter(
        player=player, column=Vizier.Column.BUILD, fulfilled=False
    )
    build_decrees_remaining = build_cards.count() + viziers.count()
    if build_decrees_remaining == 0:
        # move to next step
        next_daylight_step(player)
        return
    # otherwise, do turmoil checks
    # turmoil if no roosts left in supply
    if not BirdRoost.objects.filter(
        player=player, building_slot__isnull=False
    ).exists():
        turmoil(player)
        return

    ruled_clearings = [
        clearing
        for clearing in Clearing.objects.filter(game=player.game)
        if determine_clearing_rule(clearing) == player
    ]
    # further filter to only clearings with no roosts
    ruled_clearings = [
        clearing
        for clearing in ruled_clearings
        if BirdRoost.objects.filter(
            player=player, building_slot__clearing=clearing
        ).count()
        == 0
    ]
    # further filter to only clearings with free building slots
    ruled_clearings = [
        clearing
        for clearing in ruled_clearings
        if available_building_slot(clearing) is not None
    ]
    if len(ruled_clearings) == 0:
        # cant build if no clearings ruled or if they already have roosts or no building spots
        turmoil(player)
        return
    # if wild, then something is buildable
    if viziers.exists() or build_cards.filter(card__suit=Suit.WILD).exists():
        return
    decree_suits = {build_entry.card.suit for build_entry in build_cards}
    # filter one last time to only clearings with a suit that matches a decree suit
    ruled_clearings = [
        clearing for clearing in ruled_clearings if clearing.suit in decree_suits
    ]
    if len(ruled_clearings) == 0:
        # cant build if no clearings ruled or if they already have roosts or no building spots
        turmoil(player)
        return
    # if we get here, we have a clearing with a building slot and a suit that matches a decree suit
    return


@transaction.atomic
def turmoil(player: Player):
    """turmoil the player.
    (NOT YET IMPLEMENTED)
    --lose points,
    --clear their decree,
    --set leader to unavailable
    -- if all leaders unavailable, make them all available
    -- move the daylight step to "completed"
    -- create turmoil event (where player chooses new leader)
    """
    print("turmoil occured! not yet implemented")
    assert player.faction == Faction.BIRDS
    # lose points according to birds in decree (2 automatically from viziers)
    points_to_lose = 2
    points_to_lose += DecreeEntry.objects.filter(
        player=player, card__suit=Suit.WILD
    ).count()
    # clear the decree: disard all cards and destory the viziers
    for decree_entry in DecreeEntry.objects.filter(player=player):
        discard_card_from_decree(player, decree_entry)
    Vizier.objects.filter(player=player).delete()
    # set leader to unavailable and inactive
    current_leader = BirdLeader.objects.get(player=player, active=True)
    current_leader.active = False
    current_leader.available = False
    current_leader.save()
    # if all leaders unavailable, make them all available
    if BirdLeader.objects.filter(player=player, available=False).count() == 4:
        BirdLeader.objects.filter(player=player, available=False).update(available=True)
    # move daylight to completed
    daylight = get_phase(player)
    assert type(daylight) == BirdDaylight
    daylight.step = BirdDaylight.BirdDaylightSteps.COMPLETED
    daylight.save()
    # create turmoil event
    event = Event.objects.create(game=player.game, type=EventType.TURMOIL)
    TurmoilEvent.objects.create(event=event, player=player)


@transaction.atomic
def discard_card_from_decree(player: Player, decree_entry: DecreeEntry):
    """discards the given card from the player's Decree into the gamediscard pile"""
    # check that decree belongs to player
    if decree_entry.player != player:
        raise ValueError("Decree entry does not belong to player")
    card = decree_entry.card
    decree_entry.delete()
    # add card to discard pile
    discard_pile_entry = DiscardPileEntry.create_from_card(card)


@transaction.atomic
def turmoil_choose_new_leader(player: Player, leader: BirdLeader):
    """chooses a new leader for the given player and resolves the turmoil event
    -- leader msut be available
    """
    # check that leader is available
    if not leader.available:
        raise ValueError("Leader is not available")
    # make leader active
    leader.active = True
    leader.save()
    # resolve turmoil event
    turmoil_event = get_turmoil_event(player)
    turmoil_event.new_leader_chosen = True
    turmoil_event.save()
    event = turmoil_event.event
    event.is_resolved = True
    event.save()
