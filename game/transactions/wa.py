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
from game.transactions.battle import (
    start_battle,
)
from game.transactions.general import (
    craft_card,
    discard_card_from_hand,
    draw_card_from_deck,
    move_warriors,
    next_players_turn,
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


@transaction.atomic
def add_supporter(player: Player, card: CardsEP):
    """adds a supporter from hand to the player's stack"""
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    card_in_hand = validate_player_has_card_in_hand(player, card)
    # add card to supporter stack
    supporter = SupporterStackEntry.objects.create(
        player=player, card=card_in_hand.card
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
    # check that player can revolt
    supporters = validate_revolt(player, clearing)
    # discard supporters
    discard_supporters(player, supporters)
    # remove all enemy pieces from clearing
    for player_ in Player.objects.filter(game=player.game):
        if player_ != player:
            count = Warrior.objects.filter(clearing=clearing, player=player_).count()
            player_removes_warriors(clearing, player_, player_, count)
            # remove tokens from clearing
            for token in Token.objects.filter(clearing=clearing, player=player_):
                player_removes_token(player.game, token, player)
            # remove buildings from clearing
            for building in Building.objects.filter(
                building_slot__clearing=clearing, player=player_
            ):
                player_removes_building(player.game, building, player)
            # TODO: if vagabond, deal three hits
    # place matching base
    building_slot = available_building_slot(clearing)
    WABase.objects.filter(player=player, suit=clearing.suit).update(
        building_slot=building_slot
    )
    # gain troops
    matching_sympathy_count = WASympathy.objects.filter(
        player=player, clearing__suit=clearing.suit
    ).count()
    print(f"matching sympathy count: {matching_sympathy_count}")
    troops_in_supply = Warrior.objects.filter(player=player, clearing=None).count()
    print(f"troops in supply: {troops_in_supply}")
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


@transaction.atomic
def place_sympathy(player: Player, clearing: Clearing):
    """places sympathy at the given clearing, scoring points"""
    # get score after placing sympathy
    to_score = get_sympathy_points(player)
    # place sympathy token
    token = WASympathy.objects.filter(player=player, clearing=None).first()
    if token is None:
        raise ValueError("No sympathy token in the supply")
    token.clearing = clearing
    token.save()
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
    discard_supporters(player, supporters)
    place_sympathy(player, clearing)


@transaction.atomic
def training(player: Player, card: CardsEP):
    """trains an officer using the given card
    CHECK:
    -- card suit must match a base on the board
    RESOLVE:
    -- add officer
    -- discard card from player's hand
    """
    card_suit = Suit(card.value.suit)
    card_in_hand = validate_player_has_card_in_hand(player, card)
    matching_base = WABase.objects.filter(
        player=player, suit=card_suit, building_slot__isnull=False
    ).exists()
    if not matching_base and card_suit != Suit.WILD:
        raise ValueError("Suit does not match a base on the board")
    add_officer(player)
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
    start_battle(player.game, player.faction, defender.faction, clearing)


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
    warrior.clearing = clearing
    warrior.save()


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
    # remove warrior
    warrior.clearing = None
    warrior.save()
    # place sympathy
    place_sympathy(player, clearing)


@transaction.atomic
def end_revolt_step(player: Player):
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    birdsong = get_phase(player)
    assert type(birdsong) == WABirdsong, "Not Birdsong phase"
    assert birdsong.step == WABirdsong.WABirdsongSteps.REVOLT, "Not Revolt step"
    next_step(player)


@transaction.atomic
def end_spread_sympathy_step(player: Player):
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    birdsong = get_phase(player)
    assert type(birdsong) == WABirdsong, "Not Birdsong phase"
    assert (
        birdsong.step == WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY
    ), "Not Spread Sympathy step"
    next_step(player)


@transaction.atomic
def end_daylight_actions(player: Player):
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    daylight = get_phase(player)
    assert type(daylight) == WADaylight
    next_step(player)


@transaction.atomic
def end_evening_operations(player: Player):
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    evening = get_phase(player)
    assert type(evening) == WAEvening
    # move to next step
    next_step(player)
@transaction.atomic
def draw_cards(player: Player):
    evening = get_phase(player)
    assert type(evening) == WAEvening
    assert evening.step == WAEvening.WAEveningSteps.DRAWING, "Not Drawing step"
    # draw cards equal to bases on board + 1
    cards_to_draw = (
        WABase.objects.filter(player=player, building_slot__isnull=False).count() + 1
    )
    for _ in range(cards_to_draw):
        draw_card_from_deck(player)
    # move to next step
    next_step(player)

@transaction.atomic
def check_discard_step(player : Player):
    evening = get_phase(player)
    assert type(evening) == WAEvening
    assert evening.step == WAEvening.WAEveningSteps.DISCARDING, "Not Discarding step"
    # if over hand limit, exit out so player can handle discarding step
    if get_player_hand_size(player) > 5:
        return
    # otherwise, move to next step
    next_step(player)


@transaction.atomic
def end_turn(player: Player):
    """ends the current turn, generating the next turn and moving to the next players phase
    careful where this is called. will move evening to completed if called.
    """
    try:
        evening = get_phase(player)
        if type(evening) != WAEvening:
            raise ValueError("Not Evening phase")
        evening.step = WAEvening.WAEveningSteps.COMPLETED
        evening.save()
    except:
        pass
    WATurn.create_turn(player)
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
    craft_card(card_in_hand, cast(list[Piece], crafting_pieces))


@transaction.atomic
def pay_outrage(outrage_event: OutrageEvent, card: CardsEP):
    """player pays card to Woodland Alliance player
    -- transfers card from hand to supporter stack
    -- resolves event
    """
    outrageous_player: Player = outrage_event.outrageous_player
    outraged_player: Player = outrage_event.outraged_player
    card_in_hand = validate_card_can_pay_outrage(outrage_event, card)
    # transfer card from hand to supporter stack
    SupporterStackEntry.objects.create(player=outraged_player, card=card_in_hand.card)
    # remove card from player's hand
    card_in_hand.delete()
    # resolve event
    event: Event = outrage_event.event
    event.is_resolved = True
    event.save()
    outrage_event.card_given = True
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
def step_effect(player: Player, phase: Union[WABirdsong, WADaylight, WAEvening, None] = None):
    """ executes any 'passive' effects that should occur at a specific step
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
                    from game.transactions.crafted_cards.coffin_makers import score_coffins, release_warriors
                    coffin_player = get_coffin_makers_player(player.game)
                    if coffin_player == player:
                        score_coffins(player)
                        release_warriors(player.game)

                    saboteurs_check(player)
                case WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY:
                    pass
                case WABirdsong.WABirdsongSteps.COMPLETED:
                    from game.transactions.crafted_cards.eyrie_emigre import is_emigre
                    is_emigre(player)
                case _:
                    raise ValueError(f"Invalid step in step_effect for WA Birdsong: {phase.step.name}")
        case WADaylight():
            match phase.step:
                case WADaylight.WADaylightSteps.ACTIONS:
                    pass
                case WADaylight.WADaylightSteps.COMPLETED:
                    if not check_charm_offensive(player):
                        # ensures effect at beginning of evening is called
                        #not relevant here, but good to have the structure anyway
                        step_effect(player, None)
                case _:
                    raise ValueError(f"Invalid step in step_effect for WA Daylight: {phase.step.name}")
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