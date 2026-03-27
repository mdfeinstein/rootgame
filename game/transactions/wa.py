from game.models import Game
from game.models.game_models import Card
from game.transactions.general import draw_card_from_deck_to_hand
from game.queries.wa.supporters import can_add_supporter
from typing import Union
from game.transactions.crafted_cards.charm_offensive import check_charm_offensive
from game.transactions.crafted_cards.saboteurs import saboteurs_check

from game.transactions.crafted_cards.informants import informants_check
from typing import cast
from django.db import transaction

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.events.event import Event, EventType
from game.models.events.wa import OutrageEvent
from game.models.game_models import (
    Building,
    Clearing,
    DiscardPileEntry,
    Faction,
    HandEntry,
    Piece,
    Player,
    Suit,
    Token,
    Warrior,
)
from game.models.wa.buildings import WABase
from game.models.wa.player import OfficerEntry, SupporterStackEntry
from game.models.wa.tokens import WASympathy
from game.models.wa.turn import WABirdsong, WADaylight, WAEvening, WATurn
from game.queries.general import (
    available_building_slot,
    get_player_hand_size,
    validate_player_has_card_in_hand,
)
from game.queries.wa.crafting import validate_crafting_pieces_satisfy_requirements
from game.queries.wa.outrage import validate_card_can_pay_outrage
from game.queries.wa.supporters import (
    get_sympathy_points,
    validate_revolt,
    validate_sympathy_spread,
)
from game.queries.wa.turn import get_phase, validate_step
from game.queries.wa.warriors import get_warriors_in_supply
from game.serializers.general_serializers import PlayerPrivateSerializer
from game.transactions.general import (
    craft_card,
    discard_card_from_hand,
    draw_card_from_deck,
    move_warriors,
    next_players_turn,
    place_piece_from_supply_into_clearing,
    place_warriors_into_clearing,
    raise_score,
)
from game.transactions.removal import (
    player_removes_building,
    player_removes_token,
    player_removes_warriors,
)
from game.utility.textchoice import next_choice


@transaction.atomic
def discard_supporters(player: Player, supporters: list[SupporterStackEntry]):
    """discards the given supporters"""
    for supporter in supporters:
        card = supporter.card
        DiscardPileEntry.create_from_card(card)
        supporter.delete()


def add_supporter(player: Player, card: Card):
    """
    adds a card (from anywhere) to the players supporter stack
    Called by mobilize, outrage, etc.
    If cannot add, card goes to discard pile
    """
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    if not can_add_supporter(player):
        DiscardPileEntry.create_from_card(card)
    else:
        SupporterStackEntry.objects.create(player=player, card=card)


@transaction.atomic
def mobilize_supporter(player: Player, card: CardsEP):
    """adds a supporter from hand to the player's stack, during mobilize action"""
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    assert isinstance(get_phase(player), WADaylight), "Not day phase"
    card_in_hand = validate_player_has_card_in_hand(player, card)
    if not can_add_supporter(player):
        raise ValueError("Cannot add a supporter to the stack: no base and at limit")
    # add card to supporter stack
    add_supporter(player, card_in_hand.card)
    from game.serializers.logs.wa import log_wa_mobilize
    from game.serializers.logs.general import get_current_phase_log

    log_wa_mobilize(
        player.game,
        player,
        card_in_hand.card,
        parent=get_current_phase_log(player.game, player),
    )

    # delete card from player's hand
    card_in_hand.delete()


@transaction.atomic
def draw_card_to_supporters(player: Player):
    """draws a card from the deck to the player's supporters"""
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    card = draw_card_from_deck(player)
    add_supporter(player, card)


@transaction.atomic
def add_officer(player: Player):
    """adds an officer to the player's officer box"""
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    # check that there is a warrior in reserve
    reserve_warriors = get_warriors_in_supply(player)
    if not reserve_warriors.exists():
        raise ValueError("No warriors in reserve")
    # add officer to player's stack
    officer = OfficerEntry.objects.create(
        player=player, warrior=reserve_warriors.first()
    )


@transaction.atomic
def remove_officer(player: Player):
    """removes an officer from the player's officer box"""
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    # check that there is an officer in the box
    officer = OfficerEntry.objects.filter(player=player).first()
    if officer is None:
        raise ValueError("No officer in box")
    # remove officer from player's stack
    officer.warrior.clearing = None
    officer.warrior.save()
    officer.delete()


@transaction.atomic
def revolt(player: Player, clearing: Clearing):
    """revolts at the given clearing
    -- discards supporters
    -- removes all enemy pieces from the clearing (scoring points)
    -- places matching base in clearing
    -- gains troops equal to matching sympathetic clearings
    -- gains an officer
    """
    from game.transactions.removal import (
        player_removes_building,
        player_removes_token,
        player_removes_warriors,
    )

    # check that player can revolt
    supporters = validate_revolt(player, clearing)
    # discard supporters
    discard_supporters(player, supporters)
    score_before = player.score
    pieces_destroyed = {}  # { "Faction Label PieceTypeLabel": count }

    from game.serializers.logs.wa import log_wa_revolt
    from game.serializers.logs.general import get_current_phase_log

    # Create revolt log first so we can use it as parent for removals
    revolt_log = log_wa_revolt(
        player.game,
        player,
        [],  # placeholders
        clearing.clearing_number,
        0,
        {},
        parent=get_current_phase_log(player.game, player),
    )

    # remove all enemy pieces from clearing
    for player_ in Player.objects.filter(game=player.game):
        if player_ != player:
            faction_label = player_.get_faction_display()
            count = Warrior.objects.filter(clearing=clearing, player=player_).count()
            if count > 0:
                player_removes_warriors(
                    clearing, player_, player_, count, parent=revolt_log, skip_log=True
                )
                key = f"{faction_label} Warrior"
                pieces_destroyed[key] = pieces_destroyed.get(key, 0) + count

            # remove tokens from clearing
            for token in Token.objects.filter(clearing=clearing, player=player_):
                from game.transactions.removal import get_piece_name

                token_label = f"{faction_label} {get_piece_name(token)}"
                player_removes_token(
                    player.game, token, player, parent=revolt_log, skip_log=True
                )
                pieces_destroyed[token_label] = pieces_destroyed.get(token_label, 0) + 1

            # remove buildings from clearing
            for building in Building.objects.filter(
                building_slot__clearing=clearing, player=player_
            ):
                from game.transactions.removal import get_piece_name

                building_label = f"{faction_label} {get_piece_name(building)}"
                player_removes_building(
                    player.game, building, player, parent=revolt_log, skip_log=True
                )
                pieces_destroyed[building_label] = (
                    pieces_destroyed.get(building_label, 0) + 1
                )
            # TODO: if vagabond, deal three hits
    # place matching base
    base = WABase.objects.get(player=player, suit=clearing.suit)
    place_piece_from_supply_into_clearing(base, clearing)
    # gain troops
    matching_sympathy_count = WASympathy.objects.filter(
        player=player, clearing__suit=clearing.suit
    ).count()
    troops_in_supply = Warrior.objects.filter(player=player, clearing=None).count()
    place_warriors_into_clearing(
        player, clearing, min(matching_sympathy_count, troops_in_supply)
    )
    # gain officer, if able
    try:
        add_officer(player)
    except ValueError as e:
        if "No warriors in reserve" in str(e):
            pass
        else:
            raise e

    player.refresh_from_db()
    points_scored = player.score - score_before
    # Update the revolt log with final details
    from game.serializers.general_serializers import CardSerializer

    revolt_log.details["supporters_spent"] = CardSerializer(
        [s.card for s in supporters], many=True
    ).data
    revolt_log.details["points_scored"] = points_scored
    revolt_log.details["pieces_destroyed"] = pieces_destroyed
    revolt_log.save()


@transaction.atomic
def resolve_wa_base_removal(
    game: Game,
    wa_player: Player,
    clearing: Clearing,
    building: Building,
    parent: "GameLog" = None,
):
    """
    Rule 8.4.3: Discard all supporters matching its suit (including birds)
    Discard half of officers (rounded up)
    """
    from game.models.wa.player import SupporterStackEntry, OfficerEntry
    from game.models import Suit
    from game.serializers.logs.wa import (
        log_wa_supporters_lost,
        log_wa_officers_lost,
        log_wa_base_removed,
    )

    suit_to_match = building.suit
    wild_suit = Suit.WILD.value
    matching_supporters = SupporterStackEntry.objects.filter(
        player=wa_player, card__suit__in=[suit_to_match, wild_suit]
    )
    if matching_supporters.exists():
        log_wa_supporters_lost(
            game, wa_player, [s.card for s in matching_supporters], parent=parent
        )
        discard_supporters(wa_player, list(matching_supporters))

    officers = OfficerEntry.objects.filter(player=wa_player)
    officer_count = officers.count()
    if officer_count > 0:
        to_remove = (officer_count + 1) // 2
        log_wa_officers_lost(game, wa_player, to_remove, parent=parent)
        for officer in officers[:to_remove]:
            officer.warrior.clearing = None
            officer.warrior.save()
            officer.delete()

    log_wa_base_removed(
        game, wa_player, clearing.clearing_number, building.suit, parent=parent
    )


@transaction.atomic
def place_sympathy(player: Player, clearing: Clearing):
    """places sympathy at the given clearing, scoring points"""
    # get score after placing sympathy
    to_score = get_sympathy_points(player)
    token = WASympathy.objects.filter(player=player, clearing=None).first()
    if token is None:
        raise ValueError("No sympathy token in the supply")
    # check that there is not already sympathy in that clearing
    if WASympathy.objects.filter(player=player, clearing=clearing).exists():
        raise ValueError("Player already has a sympathy token in this clearing")
    place_piece_from_supply_into_clearing(token, clearing)
    # score points
    raise_score(player, to_score)


@transaction.atomic
def spread_sympathy(player: Player, clearing: Clearing):
    """spreads sympathy at the given clearing
    -- discards supporters
    -- places sympathy token
    -- score points
    """
    # check that player can spread sympathy
    supporters = validate_sympathy_spread(player, clearing)
    score_before = player.score

    discard_supporters(player, supporters)
    place_sympathy(player, clearing)

    player.refresh_from_db()
    points_scored = player.score - score_before

    supporters_spent = [s.card for s in supporters]

    from game.serializers.logs.wa import log_wa_spread_sympathy
    from game.serializers.logs.general import get_current_phase_log

    log_wa_spread_sympathy(
        player.game,
        player,
        supporters_spent,
        clearing.clearing_number,
        points_scored,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def training(player: Player, card: CardsEP):
    """trains an officer using the given card
    CHECK:
    -- card suit must match a base on the board
    RESOLVE:
    -- add officer
    -- discard card from player's hand
    """
    card_suit = Suit(card.value.suit.value)
    card_in_hand = validate_player_has_card_in_hand(player, card)
    matching_base = WABase.objects.filter(
        player=player, suit=card_suit, building_slot__isnull=False
    ).exists()
    if not matching_base and card_suit != Suit.WILD:
        raise ValueError("Suit does not match a base on the board")
    add_officer(player)

    from game.serializers.logs.wa import log_wa_train
    from game.serializers.logs.general import get_current_phase_log

    log_wa_train(
        player.game,
        player,
        card_in_hand.card,
        parent=get_current_phase_log(player.game, player),
    )

    discard_card_from_hand(player, card_in_hand)


@transaction.atomic
def operation_move(
    player: Player, start_clearing: Clearing, end_clearing: Clearing, count: int
):
    """moves warriors from start_clearing to end_clearing
    CHECK:
    -- there are unused officers
    -- movement checks handled by internal transaction
    RESOLVE:
    -- mark officer as used
    -- move warriors
    """
    # check that there are unused officers
    officer = OfficerEntry.objects.filter(player=player, used=False).first()
    if officer is None:
        raise ValueError("No unused officers")
    # mark officer as used
    officer.used = True
    officer.save()
    # execute move
    move_warriors(player, start_clearing, end_clearing, count)

    from game.serializers.logs.general import log_move, get_current_phase_log

    log_move(
        player.game,
        player,
        count,
        start_clearing.clearing_number,
        end_clearing.clearing_number,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def operation_battle(player: Player, defender: Player, clearing: Clearing):
    """battles the given defender in the given clearing
    CHECK:
    -- there are unused officers
    -- battle checks handled by internal transaction
    RESOLVE:
    -- mark officer as used
    -- battle
    """

    # check that there are unused officers
    officer = OfficerEntry.objects.filter(player=player, used=False).first()
    if officer is None:
        raise ValueError("No unused officers")
    # mark officer as used
    officer.used = True
    officer.save()
    # execute battle
    from game.transactions.battle import start_battle, log_battle_start

    battle = start_battle(player.game, player.faction, defender.faction, clearing)

    from game.serializers.logs.wa import log_wa_military_operation
    from game.serializers.logs.general import get_current_phase_log

    parent = log_wa_military_operation(
        player.game,
        player,
        "Battle",
        parent=get_current_phase_log(player.game, player),
    )

    log_battle_start(battle, player, parent=parent)


@transaction.atomic
def operation_recruit(player: Player, clearing: Clearing):
    """recruits warriors at the given clearing
    CHECK:
    -- there are unused officers
    -- WA has a base in that clearing
    RESOLVE:
    -- mark officer as used
    -- recruit
    """
    # check that there are unused officers
    officer = OfficerEntry.objects.filter(player=player, used=False).first()
    if officer is None:
        raise ValueError("No unused officers")
    # check that there is a base in that clearing
    if not WABase.objects.filter(
        player=player, building_slot__clearing=clearing
    ).exists():
        raise ValueError("No base in that clearing")
    # mark officer as used
    officer.used = True
    officer.save()
    # execute recruit
    warrior = get_warriors_in_supply(player).first()
    if warrior is None:
        raise ValueError("No warriors in supply")
    place_piece_from_supply_into_clearing(warrior, clearing)

    from game.serializers.logs.wa import log_wa_military_operation
    from game.serializers.logs.general import get_current_phase_log

    log_wa_military_operation(
        player.game,
        player,
        "Recruit",
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def operation_organize(player: Player, clearing: Clearing):
    """
    Organize in the given clearing by removing a warrior
    and placing a sympathy there
    """
    # check that there are unused officers
    officer = OfficerEntry.objects.filter(player=player, used=False).first()
    if officer is None:
        raise ValueError("No unused officers")
    # check that there is a warrior in the clearing
    warrior = Warrior.objects.filter(clearing=clearing, player=player).first()
    if warrior is None:
        raise ValueError("No warrior in that clearing")
    # mark officer as used
    officer.used = True
    officer.save()
    score_before = player.score

    # remove warrior
    warrior.clearing = None
    warrior.save()
    # place sympathy
    place_sympathy(player, clearing)

    player.refresh_from_db()
    points_scored = player.score - score_before

    from game.serializers.logs.wa import log_wa_organize
    from game.serializers.logs.general import get_current_phase_log

    log_wa_organize(
        player.game,
        player,
        clearing.clearing_number,
        points_scored,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def end_revolt_step(player: Player):
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    birdsong = get_phase(player)
    assert isinstance(birdsong, WABirdsong), "Not Birdsong phase"
    assert birdsong.step == WABirdsong.WABirdsongSteps.REVOLT, "Not Revolt step"
    next_step(player)


@transaction.atomic
def end_spread_sympathy_step(player: Player):
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    birdsong = get_phase(player)
    assert isinstance(birdsong, WABirdsong), "Not Birdsong phase"
    assert (
        birdsong.step == WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY
    ), "Not Spread Sympathy step"
    next_step(player)


@transaction.atomic
def end_daylight_actions(player: Player):
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    daylight = get_phase(player)
    assert isinstance(daylight, WADaylight)
    next_step(player)


@transaction.atomic
def end_evening_operations(player: Player):
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    evening = get_phase(player)
    assert isinstance(evening, WAEvening)
    # move to next step
    next_step(player)


@transaction.atomic
def draw_cards(player: Player):
    evening = get_phase(player)
    assert isinstance(evening, WAEvening)
    assert evening.step == WAEvening.WAEveningSteps.DRAWING, "Not Drawing step"
    # draw cards equal to bases on board + 1
    cards_to_draw = (
        WABase.objects.filter(player=player, building_slot__isnull=False).count() + 1
    )
    drawn_cards = []
    for _ in range(cards_to_draw):
        hand_entry = draw_card_from_deck_to_hand(player)
        drawn_cards.append(hand_entry.card)

    from game.serializers.logs.general import log_draw, get_current_phase_log

    log_draw(
        player.game,
        player,
        drawn_cards,
        parent=get_current_phase_log(player.game, player),
    )
    # move to next step
    next_step(player)


@transaction.atomic
def check_discard_step(player: Player):
    evening = get_phase(player)
    assert isinstance(evening, WAEvening)
    assert evening.step == WAEvening.WAEveningSteps.DISCARDING, "Not Discarding step"
    # if over hand limit, exit out so player can handle discarding step
    if get_player_hand_size(player) > 5:
        return
    # otherwise, move to next step
    next_step(player)


@transaction.atomic
def create_wa_turn(player: Player):
    # create turn
    turn = WATurn.create_turn(player)

    from game.serializers.logs.general import log_turn, log_phase

    turn_log = log_turn(player.game, player, turn_number=turn.turn_number + 1)
    log_phase(player.game, player, "Birdsong", parent=turn_log)


@transaction.atomic
def end_turn(player: Player):
    """ends the current turn, generating the next turn and moving to the next players phase
    careful where this is called. will move evening to completed if called.
    """
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
    # reset crafting pieces
    WASympathy.objects.filter(player=player).update(crafted_with=False)
    # reset officers
    OfficerEntry.objects.filter(player=player).update(used=False)


@transaction.atomic
def wa_craft_card(player: Player, card: CardsEP, crafting_pieces: list[WASympathy]):
    """crafts a card with the given symapthy tokens."""
    validate_step(player, WADaylight.WADaylightSteps.ACTIONS)
    card_in_hand = validate_player_has_card_in_hand(player, card)
    if not validate_crafting_pieces_satisfy_requirements(player, card, crafting_pieces):
        raise ValueError("Not enough crafting pieces to craft card")
    card_model = card_in_hand.card
    craft_card(card_in_hand, cast(list[Piece], crafting_pieces))

    from game.serializers.logs.general import log_craft, get_current_phase_log

    log_craft(
        player.game,
        player,
        card_model,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def pay_outrage(outrage_event: OutrageEvent, card: CardsEP):
    """player pays card to Woodland Alliance player
    -- transfers card from hand to supporter stack
    -- resolves event
    """
    outrageous_player: Player = outrage_event.outrageous_player
    outraged_player: Player = outrage_event.outraged_player
    card_in_hand = validate_card_can_pay_outrage(outrage_event, card)
    card = card_in_hand.card
    # add card to outraged player's supporters (if able, else will discard)
    add_supporter(outraged_player, card)
    # remove card from player's hand
    card_in_hand.delete()
    # resolve event
    event: Event = outrage_event.event
    event.is_resolved = True
    event.save()
    outrage_event.card_given = True

    # Update log if it exists
    from game.models.game_log import GameLog

    log = GameLog.objects.filter(outrage_event=outrage_event).first()
    if log:
        from game.serializers.logs.wa import WAOutrageLogDetailsSerializer
        from game.serializers.general_serializers import CardSerializer

        details = dict(log.details)
        details["card_given"] = True
        details["card"] = CardSerializer(card).data
        log.details = details
        log.save()

    outrage_event.save()


@transaction.atomic
def next_step(player: Player):
    """
    moves to next step in the current phase or next phase, launching events if necessary
    e.g.: for card effects that need to be triggered at a specific step
    """
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
    # execute any passive effects that should occur at the step that was just moved into
    phase.save()
    step_effect(player, phase)


@transaction.atomic
def step_effect(
    player: Player, phase: Union[WABirdsong, WADaylight, WAEvening, None] = None
):
    """executes any 'passive' effects that should occur at a specific step
    ex: drawing or launching events
    typically called from next_step
    """
    if phase is None:
        phase = get_phase(player)
    match phase:
        case WABirdsong():
            match phase.step:
                case WABirdsong.WABirdsongSteps.NOT_STARTED:
                    pass
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

                    saboteurs_check(player)
                case WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY:
                    pass
                case WABirdsong.WABirdsongSteps.COMPLETED:
                    from game.transactions.crafted_cards.eyrie_emigre import is_emigre

                    if not is_emigre(player):
                        from game.serializers.logs.general import (
                            log_phase,
                            get_current_turn_log,
                        )

                        log_phase(
                            player.game,
                            player,
                            "Daylight",
                            parent=get_current_turn_log(player.game, player),
                        )
                        step_effect(player, None)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for WA Birdsong: {phase.step.name}"
                    )
        case WADaylight():
            match phase.step:
                case WADaylight.WADaylightSteps.ACTIONS:
                    pass
                case WADaylight.WADaylightSteps.COMPLETED:
                    if not check_charm_offensive(player):
                        from game.serializers.logs.general import (
                            log_phase,
                            get_current_turn_log,
                        )

                        log_phase(
                            player.game,
                            player,
                            "Evening",
                            parent=get_current_turn_log(player.game, player),
                        )
                        step_effect(player, None)
                case _:
                    raise ValueError(
                        f"Invalid step in step_effect for WA Daylight: {phase.step.name}"
                    )
        case WAEvening():
            match phase.step:
                case WAEvening.WAEveningSteps.MILITARY_OPERATIONS:
                    pass
                case WAEvening.WAEveningSteps.DRAWING:
                    is_informants = informants_check(player)
                    if not is_informants:
                        draw_cards(player)
                case WAEvening.WAEveningSteps.DISCARDING:
                    check_discard_step(player)
                case WAEvening.WAEveningSteps.COMPLETED:
                    end_turn(player)
                case _:
                    raise ValueError(f"Invalid step in step_effect: {phase.step.name}")
        case _:
            raise ValueError("Invalid phase")
