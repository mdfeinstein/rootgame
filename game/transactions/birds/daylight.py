from django.db import transaction
from typing import cast

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.buildings import BirdRoost
from game.models.birds.player import DecreeEntry, Vizier
from game.models.birds.turn import BirdDaylight
from game.models.game_models import Clearing, Faction, Piece, Player, Suit, Warrior
from game.queries.birds.crafting import (
    get_all_unused_roosts,
    validate_crafting_pieces_satisfy_requirements,
)
from game.queries.birds.turn import get_phase, validate_step
from game.queries.general import (
    determine_clearing_rule,
    get_player_hand_size,
    player_has_pieces_in_clearing,
    validate_has_legal_moves,
    validate_player_has_card_in_hand,
    warrior_count_in_supply,
)
from game.transactions.general import craft_card, move_warriors
from game.errors import UnavailableActionError, IllegalActionError, InternalGameError


@transaction.atomic
def bird_craft_card(player: Player, card: CardsEP, crafting_pieces: list[BirdRoost]):
    """crafts a card with the given pieces. If it is an item, scores the points and discards it
    If not, moves the card to the player's crafted card box.
    raises ValueError if not enough crafting pieces to craft the card or other issues
    """
    validate_step(player, BirdDaylight.BirdDaylightSteps.CRAFTING)
    card_in_hand = validate_player_has_card_in_hand(player, card)
    if not validate_crafting_pieces_satisfy_requirements(player, card, crafting_pieces):
        raise IllegalActionError("Not enough crafting pieces to craft card")
    card_model = card_in_hand.card
    craft_card(card_in_hand, cast(list[Piece], crafting_pieces))

    from game.serializers.logs.general import log_craft, get_current_phase_log

    log_craft(
        player.game,
        player,
        card_model,
        parent=get_current_phase_log(player.game, player),
    )
    # if no more crafting pieces, move to next step
    if get_player_hand_size(player) == 0 or get_all_unused_roosts(player).count() == 0:
        from game.transactions.birds.turn import next_step

        next_step(player)


@transaction.atomic
def bird_recruit_action(
    player: Player, roost: BirdRoost, decree_entry: DecreeEntry | Vizier
):
    """recruits warriors at the given roost clearing using the decree entry
    raises ValueError if there is an issue
    """
    from game.transactions.birds.daylight import recruit_turmoil_check
    from game.transactions.general import place_warriors_into_clearing
    from game.transactions.birds.turmoil import turmoil

    validate_step(player, BirdDaylight.BirdDaylightSteps.RECRUITING)
    # get clearing, checking that it is on the board
    clearing = roost.building_slot.clearing
    if clearing is None:
        raise IllegalActionError("Roost is not on the board")
    # check that decree_entry is in the correct column and that it has not been used
    if decree_entry.fulfilled:
        raise IllegalActionError("This decree card has already been used")
    if decree_entry.column != DecreeEntry.Column.RECRUIT:
        raise IllegalActionError("Decree card is not in the recruit column")
    # check that the decree suit matches the roost suit
    decree_suit = (
        decree_entry.card.suit if type(decree_entry) == DecreeEntry else Suit.WILD
    )
    if decree_suit != clearing.suit and decree_suit != Suit.WILD:
        raise IllegalActionError("Decree suit does not match roost suit")
    # determine number to recruit, based on leader
    from game.models.birds.player import BirdLeader

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

    from game.serializers.logs.birds import log_birds_decree_action
    from game.serializers.logs.general import get_current_phase_log

    log_birds_decree_action(
        player.game,
        player,
        "recruit",
        clearing.clearing_number,
        parent=get_current_phase_log(player.game, player),
    )

    # check if turmoil or next_step
    recruit_turmoil_check(player)


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
    from game.transactions.birds.daylight import move_turmoil_check

    validate_step(player, BirdDaylight.BirdDaylightSteps.MOVING)
    # check that clearings are in the right game
    if player.game != origin_clearing.game != target_clearing.game:
        raise UnavailableActionError(
            "Clearings are not in the same game as each other or player"
        )
    # check that decree_entry is in the correct column and that it has not been used
    if decree_entry.fulfilled:
        raise IllegalActionError("This decree card has already been used")
    if decree_entry.column != DecreeEntry.Column.MOVE:
        raise IllegalActionError("Decree card is not in the move column")
    # check that the decree suit matches the origin clearing suit
    decree_suit = (
        decree_entry.card.suit if type(decree_entry) == DecreeEntry else Suit.WILD
    )
    if decree_suit != origin_clearing.suit and decree_suit != Suit.WILD:
        raise IllegalActionError("Decree suit does not match origin clearing suit")
    # move warriors (movement checks handled in this transaction function)
    move_warriors(player, origin_clearing, target_clearing, number)
    # mark decree entry as used
    decree_entry.fulfilled = True
    decree_entry.save()

    from game.serializers.logs.birds import log_birds_decree_action
    from game.serializers.logs.general import get_current_phase_log

    log_birds_decree_action(
        player.game,
        player,
        "move",
        origin_clearing.clearing_number,
        parent=get_current_phase_log(player.game, player),
    )

    # check if turmoil or next_step
    move_turmoil_check(player)


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
    from game.transactions.birds.daylight import battle_turmoil_check
    from game.transactions.battle import start_battle, log_battle_start

    validate_step(player, BirdDaylight.BirdDaylightSteps.BATTLING)
    # check that the defender is in the same game as the player
    if defender.game != player.game != clearing.game:
        raise UnavailableActionError(
            "Defender is not in the same game as the player and the clearing"
        )
    # check decree entry not used and matches clearing
    if decree_entry.fulfilled:
        raise IllegalActionError("This decree card has already been used")
    if decree_entry.column != DecreeEntry.Column.BATTLE:
        raise IllegalActionError("Decree card is not in the battle column")
    decree_suit = (
        decree_entry.card.suit if type(decree_entry) == DecreeEntry else Suit.WILD
    )
    if decree_suit != clearing.suit and decree_suit != Suit.WILD:
        raise IllegalActionError("Decree suit does not match clearing suit")
    # battle checks are in start_battle
    battle = start_battle(
        player.game, Faction(player.faction), Faction(defender.faction), clearing
    )
    # use decree entry
    decree_entry.fulfilled = True
    decree_entry.save()

    from game.serializers.logs.birds import log_birds_decree_action
    from game.serializers.logs.general import get_current_phase_log

    parent = log_birds_decree_action(
        player.game,
        player,
        "battle",
        clearing.clearing_number,
        parent=get_current_phase_log(player.game, player),
    )

    log_battle_start(battle, player, parent=parent)

    # check if turmoil or next_step
    battle_turmoil_check(player)


@transaction.atomic
def bird_build_action(
    player: Player, clearing: Clearing, decree_entry: DecreeEntry | Vizier
):
    """builds a roost in the given clearing using the decree_entry provided"""
    from game.transactions.birds.daylight import build_turmoil_check
    from game.transactions.general import place_piece_from_supply_into_clearing

    validate_step(player, BirdDaylight.BirdDaylightSteps.BUILDING)
    # check that decree entry is in the correct column and that it has not been used
    if decree_entry.fulfilled:
        raise IllegalActionError("This decree card has already been used")
    if decree_entry.column != DecreeEntry.Column.BUILD:
        raise IllegalActionError("Decree card is not in the build column")
    # check that the decree suit matches the clearing suit
    decree_suit = (
        decree_entry.card.suit if type(decree_entry) == DecreeEntry else Suit.WILD
    )
    if decree_suit != clearing.suit and decree_suit != Suit.WILD:
        raise IllegalActionError("Decree suit does not match clearing suit")
    # check that the clearing is in the right game
    if clearing.game != player.game:
        raise UnavailableActionError("Clearing is not in the same game as player")
    # check that player rules this clearing
    if determine_clearing_rule(clearing) != player:
        raise IllegalActionError("Player does not rule this clearing")
    # place roost (which checks fro free building slot and no other roost)
    from game.transactions.birds.birdsong import place_roost

    place_roost(player, clearing)
    # use decree entry
    decree_entry.fulfilled = True
    decree_entry.save()

    from game.serializers.logs.birds import log_birds_decree_action
    from game.serializers.logs.general import get_current_phase_log

    log_birds_decree_action(
        player.game,
        player,
        "build",
        clearing.clearing_number,
        parent=get_current_phase_log(player.game, player),
    )

    # check if turmoil or next_step
    build_turmoil_check(player)


# Turmoil check functions that need to be in this module (they're called from step_effect)
@transaction.atomic
def recruit_turmoil_check(player: Player):
    """
    initiates turmoil if the player can't recruit but needs to,
    either because no warriors in supply or because no matching roosts remaining.
    Also, moves to next step if no recruit decrees present
    """
    from game.transactions.birds.turn import next_step
    from game.transactions.birds.turmoil import turmoil

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
        next_step(player)
        return
    # otherwise, do turmoil checks
    if warrior_count_in_supply(player) == 0 and recruit_decrees_remaining != 0:
        turmoil(player)
        print("turmoiled because no warriors in supply")
        return
    # if no remaining recruit decrees are possible, turmoil
    # if wild in recruit (and sitll a roost), then more to do this phase, exit out
    if (
        recruit_cards.filter(card__suit=Suit.WILD).exists() or viziers.exists()
    ) and BirdRoost.objects.filter(
        player=player, building_slot__isnull=False
    ).count() != 0:
        print("no turmoil: wild card or vizier")
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
        print("turmoiled because no overlap between suits of decrees and roost")


@transaction.atomic
def move_turmoil_check(player: Player):
    """
    initiates turmoil if the player can't move but needs to,
    possible reasons:
    -- no warriors present in remaining decree suits
    -- warriors in remaining decree suits can not legally move
    Also, moves to next step if no move decrees present
    """
    from game.transactions.birds.turn import next_step
    from game.transactions.birds.turmoil import turmoil

    move_cards = DecreeEntry.objects.filter(
        player=player, column=DecreeEntry.Column.MOVE, fulfilled=False
    )
    viziers = Vizier.objects.filter(
        player=player, column=Vizier.Column.MOVE, fulfilled=False
    )
    move_decrees_remaining = move_cards.count() + viziers.count()
    if move_decrees_remaining == 0:
        # move to next step
        next_step(player)
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
            except IllegalActionError as e:
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
        except IllegalActionError as e:
            pass
    # if we get here, no legal moves. turmoil
    turmoil(player)


@transaction.atomic
def battle_turmoil_check(player: Player):
    """
    initiates turmoil if the player can't battle but needs to,
    possible reasons:
    -- no warriors present in remaining decree suits
    -- warriors in remaining decree suits have no one to battle
    Also, moves to next step if no battle decrees present
    """
    from game.transactions.birds.turn import next_step
    from game.transactions.birds.turmoil import turmoil

    battle_cards = DecreeEntry.objects.filter(
        player=player, column=DecreeEntry.Column.BATTLE, fulfilled=False
    )
    viziers = Vizier.objects.filter(
        player=player, column=Vizier.Column.BATTLE, fulfilled=False
    )
    battle_decrees_remaining = battle_cards.count() + viziers.count()
    if battle_decrees_remaining == 0:
        # move to next step
        next_step(player)
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
    # if we get here, no legal battles. turmoil
    turmoil(player)


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
    from game.transactions.birds.turn import next_step
    from game.transactions.birds.turmoil import turmoil
    from game.queries.general import available_building_slot

    build_cards = DecreeEntry.objects.filter(
        player=player, column=DecreeEntry.Column.BUILD, fulfilled=False
    )
    viziers = Vizier.objects.filter(
        player=player, column=Vizier.Column.BUILD, fulfilled=False
    )
    build_decrees_remaining = build_cards.count() + viziers.count()
    if build_decrees_remaining == 0:
        # move to next step
        next_step(player)
        return
    # otherwise, do turmoil checks
    # turmoil if no roosts left in supply
    if not BirdRoost.objects.filter(player=player, building_slot__isnull=True).exists():
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
