from game.models.cats import CatKeep
from game.queries.general import validate_player_has_crafted_card
from game.queries.general import validate_legal_move
from random import shuffle
import warnings
from django.db import transaction

from game.models import (
    Building,
    Card,
    Clearing,
    CraftableItemEntry,
    CraftedCardEntry,
    CraftedItemEntry,
    CraftingPieceMixin,
    DeckEntry,
    DiscardPileEntry,
    Game,
    HandEntry,
    Item,
    Piece,
    Player,
    Suit,
    Token,
    Warrior,
)
from game.models.dominance import DominanceSupplyEntry, ActiveDominanceEntry
from game.models.game_models import Faction
from game.queries.general import (
    determine_clearing_rule,
    warrior_count_in_clearing,
    get_adjacent_clearings,
)
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.game_data.cards.exiles_and_partisans import Card as CardDetails
from game.game_data.general.crafting import crafting_piece_models
from django.db import models

from game.queries.wa.outrage import move_triggers_outrage


@transaction.atomic
def reshuffle_discard_into_deck(game: Game):
    """reshuffles the discard pile into the deck"""
    assert len(DeckEntry.objects.filter(game=game)) == 0, "deck is not empty"
    # query all cards in discard pile
    cards_in_discard = list(DiscardPileEntry.objects.filter(game=game))
    shuffle(cards_in_discard)
    # create deck entries for each card
    deck_entries = [
        DeckEntry(game=game, card=card_in_discard.card, spot=i)
        for i, card_in_discard in enumerate(cards_in_discard)
    ]
    DeckEntry.objects.bulk_create(deck_entries)
    # delete cards from discard pile
    DiscardPileEntry.objects.filter(game=game).delete()


@transaction.atomic
def draw_card_from_deck(player: Player) -> Card:
    """draws a card from the deck and returns the card object"""
    # select top card from deck
    card_in_deck = DeckEntry.objects.filter(game=player.game).first()
    if card_in_deck is None:
        reshuffle_discard_into_deck(player.game)
        card_in_deck = DeckEntry.objects.filter(game=player.game).first()
    # add card to player's hand
    assert card_in_deck is not None, "card_in_deck is none"
    card = card_in_deck.card
    # delete card from deck
    card_in_deck.delete()
    return card


@transaction.atomic
def draw_card_from_deck_to_hand(player: Player) -> HandEntry:
    """draws a card from the deck and adds it to the player's hand"""
    # select top card from deck
    card = draw_card_from_deck(player)
    card_in_hand = HandEntry.objects.create(player=player, card=card)
    return card_in_hand


@transaction.atomic
def discard_card_from_hand(player: Player, card_in_hand: HandEntry):
    # check that card is in player's hand
    if player != card_in_hand.player:
        raise ValueError("card is not in player's hand")
    # add card to discard pile
    # add card to discard pile
    if card_in_hand.card.dominance:
        # Dominance cards go to the dominance supply
        DominanceSupplyEntry.objects.create(game=player.game, card=card_in_hand.card)
    else:
        spot = DiscardPileEntry.objects.filter(game=player.game).count()
        DiscardPileEntry(game=player.game, card=card_in_hand.card, spot=spot).save()
    # DiscardPileEntry.create_from_card(card_in_hand.card)
    # delete card from player's hand
    card_in_hand.delete()


@transaction.atomic
def move_warriors(
    player: Player,
    clearing_start: Clearing,
    clearing_end: Clearing,
    number: int,
    ignore_rule: bool = False,
):
    """moves warriors from one clearing to another"""
    from game.transactions.outrage import create_outrage_event

    if number <= 0:
        raise ValueError("Cannot move 0 warriors")
    warriors = list(
        Warrior.objects.filter(clearing=clearing_start, player=player)[:number]
    )
    if len(warriors) != number:
        raise ValueError("not enough warriors in clearing to move")
    # check adjacency and rulership
    validate_legal_move(player, clearing_start, clearing_end, ignore_rule=ignore_rule)
    # update clearing of warriors
    for warrior in warriors:
        warrior.clearing = clearing_end
    Warrior.objects.bulk_update(warriors, ["clearing"])
    # faction specific interactions:
    if move_triggers_outrage(player, clearing_end):
        wa_player = Player.objects.get(
            game=player.game, faction=Faction.WOODLAND_ALLIANCE
        )
        create_outrage_event(clearing_end, player, wa_player)


@transaction.atomic
def place_piece_from_supply_into_clearing(piece: Piece, clearing: Clearing):
    """
    places a piece from the supply into a clearing, checking if able
    -- checks if piece in supply
    -- non-cats placing into keep clearing will be blocked
    -- later: crows snare will block
    """
    if piece.clearing is not None:
        raise ValueError("piece is already in a clearing")
    # check for keep clearing, if relevant
    if piece.player.faction != Faction.CATS:
        try:
            keep = CatKeep.objects.get(clearing=clearing)
            raise ValueError("Cannot place non-cat piece in keep clearing")
        except CatKeep.DoesNotExist:
            pass
    piece.clearing = clearing
    piece.save()


@transaction.atomic
def place_warriors_into_clearing(player: Player, clearing: Clearing, number: int):
    """places warriors into the given clearing.
    will raise if not enough warriors in the supply
    """
    count_in_supply = Warrior.objects.filter(clearing=None, player=player).count()
    if count_in_supply < number:
        raise ValueError(
            f"Not enough warriors in supply to place {number} warriors. "
            f"In supply: {count_in_supply}"
        )
    for w in Warrior.objects.filter(clearing=None, player=player)[:number]:
        place_piece_from_supply_into_clearing(w, clearing)


@transaction.atomic
def craft_card(card_in_hand: HandEntry, crafting_pieces: list[Piece]):
    """crafts a card with the given pieces. If it is an item, scores the points and discards it
    If not, moves the card to the player's crafted card box.
    NOTE: this function does not check if the player has enough crafting pieces to craft the card.
    It is assumed that the caller has already done this check, since this may be faction specific.
    The faction crafting transactions should call this function with the appropriate pieces.
    """
    card: CardDetails = card_in_hand.card.enum.value
    if not card.craftable:
        raise ValueError("card is not craftable")
    item = card.item
    points = card.crafted_points
    crafting_cost = card.cost

    # check that card is an item card
    if item is not None:
        # check that item is still in the craftable pool
        if not CraftableItemEntry.objects.filter(item__item_type=item.value).exists():
            raise ValueError("item is not in the craftable pool")
    else:
        # check that player does not have this same card type already crafted
        if CraftedCardEntry.objects.filter(
            card__card_type=card_in_hand.card.card_type, player=card_in_hand.player
        ).exists():
            raise ValueError("player already has this card type crafted")

    # check that crafting pieces are actually crafting pieces
    for crafting_piece in crafting_pieces:
        if not issubclass(type(crafting_piece), CraftingPieceMixin):
            raise ValueError("not all crafting pieces are CraftingPieceMixins")
    # check that pieces havent been used yet
    for crafting_piece in crafting_pieces:
        assert isinstance(crafting_piece, CraftingPieceMixin)
        if crafting_piece.crafted_with:
            raise ValueError("some pieces have already been used")
    # check that they belong to the player
    for crafting_piece in crafting_pieces:
        if crafting_piece.player != card_in_hand.player:
            raise ValueError("player does not own the pieces")
    # assume that the caller has already checked that the player has enough crafting pieces to craft the card
    # mark crafting pieces as used
    for crafting_piece in crafting_pieces:
        assert isinstance(crafting_piece, CraftingPieceMixin)
        crafting_piece.crafted_with = True
        crafting_piece.save()

    if item is not None:
        # move item from pool to player's inventory
        item_from_pool = CraftableItemEntry.objects.filter(
            item__item_type=item.value
        ).first()
        assert item_from_pool is not None, "item not in pool"
        item = item_from_pool.item
        CraftedItemEntry(player=card_in_hand.player, item=item).save()
        item_from_pool.delete()
        try:
            validate_player_has_crafted_card(
                card_in_hand.player, CardsEP.MASTER_ENGRAVERS
            )
            has_master_engravers = True
        except ValueError:
            has_master_engravers = False

        # update score
        # Birds Disdain for Trade: items only score 1VP unless Builder leader
        if card_in_hand.player.faction == Faction.BIRDS:
            from game.models.birds.player import BirdLeader

            leader = BirdLeader.objects.get(player=card_in_hand.player, active=True)
            if leader.leader != BirdLeader.BirdLeaders.BUILDER.value:
                points = 1

        card_in_hand.player.score += points
        if has_master_engravers:
            card_in_hand.player.score += 1
        card_in_hand.player.save()
        # discard card from player's hand
        discard_card_from_hand(card_in_hand.player, card_in_hand)
    else:  # not an item card
        # move card from player's hand to player's crafted card box
        CraftedCardEntry(player=card_in_hand.player, card=card_in_hand.card).save()
        # delete card from player's hand
        card_in_hand.delete()

    # Murine Brokers check: Whenever ANY OTHER player crafts an item card
    if item is not None:
        other_players = Player.objects.filter(game=card_in_hand.player.game).exclude(
            pk=card_in_hand.player.pk
        )
        for other_player in other_players:
            try:
                validate_player_has_crafted_card(other_player, CardsEP.MURINE_BROKERS)
                draw_card_from_deck_to_hand(other_player)
            except ValueError:
                pass


@transaction.atomic
def next_players_turn(game: Game):
    """moves to the next player's turn"""
    player_count = Player.objects.filter(game=game).count()
    game.current_turn = (game.current_turn + 1) % player_count
    game.save()
    # call next_step on the new player's turn to activate any beginning of turn effects
    new_player = Player.objects.get(game=game, turn_order=game.current_turn)

    # Check Dominance Victory at start of turn
    from game.transactions.dominance import check_dominance_victory

    check_dominance_victory(new_player)
    # Refresh logic in case game ended?
    game.refresh_from_db()
    if game.status == Game.GameStatus.COMPLETED:
        return

    # reset used crafted cards
    CraftedCardEntry.objects.filter(player=new_player).update(
        used=CraftedCardEntry.UsedChoice.UNUSED
    )
    next_step(new_player)


@transaction.atomic
def raise_score(player: Player, amount: int):
    """
    raise a player's score, and check any relevant score related conditions, such as winning the game.
    """

    # Check if player has active dominance
    try:
        if player.active_dominance:
            # Player has active dominance, score does not increase and standard victory check is skipped
            return
    except ActiveDominanceEntry.DoesNotExist:
        pass

    player.score += amount
    player.save()
    if player.score >= 30:
        game = player.game
        game.status = Game.GameStatus.COMPLETED
        game.save()


@transaction.atomic
def next_step(player: Player):
    """moves to the next step in the current player's turn"""
    match player.faction:
        case Faction.CATS:
            from game.transactions.cats import next_step

            next_step(player)
        case Faction.WOODLAND_ALLIANCE:
            from game.transactions.wa import next_step

            next_step(player)
        case Faction.BIRDS:
            from game.transactions.birds import next_step

            next_step(player)


@transaction.atomic
def step_effect(player: Player):
    match player.faction:
        case Faction.CATS:
            from game.transactions.cats import step_effect

            step_effect(player)
        case Faction.WOODLAND_ALLIANCE:
            from game.transactions.wa import step_effect

            step_effect(player)
        case Faction.BIRDS:
            from game.transactions.birds import step_effect

            step_effect(player)
