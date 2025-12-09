from random import shuffle
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
from game.queries.general import determine_clearing_rule, warrior_count_in_clearing
from game.game_data.cards.exiles_and_partisans import Card as CardDetails
from game.game_data.general.crafting import crafting_piece_models
from django.db import models


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
def draw_card_from_deck(player: Player):
    """draws a card from the deck and adds it to the player's hand"""
    # select top card from deck
    card_in_deck = DeckEntry.objects.filter(game=player.game).first()
    if card_in_deck is None:
        reshuffle_discard_into_deck(player.game)
        card_in_deck = DeckEntry.objects.filter(game=player.game).first()
    # add card to player's hand
    assert card_in_deck is not None, "card_in_deck is none"
    HandEntry(player=player, card=card_in_deck.card).save()
    # delete card from deck
    assert card_in_deck is not None, "card_in_deck is none"
    card_in_deck.delete()


@transaction.atomic
def discard_card_from_hand(player: Player, card_in_hand: HandEntry):
    # check that card is in player's hand
    if player != card_in_hand.player:
        raise ValueError("card is not in player's hand")
    # add card to discard pile
    spot = DiscardPileEntry.objects.filter(game=player.game).count()
    DiscardPileEntry(game=player.game, card=card_in_hand.card, spot=spot).save()
    # delete card from player's hand
    card_in_hand.delete()


@transaction.atomic
def move_warriors(
    player: Player, clearing_start: Clearing, clearing_end: Clearing, number: int
):
    """moves warriors from one clearing to another"""
    warriors = list(
        Warrior.objects.filter(clearing=clearing_start, player=player)[:number]
    )
    if len(warriors) != number:
        raise ValueError("not enough warriors in clearing to move")
    # check clearing adjacency
    if not clearing_start.connected_clearings.filter(pk=clearing_end.pk).exists():
        raise ValueError("clearing_start is not adjacent to clearing_end")
    # check rule of clearings
    rule_target_or_origin = determine_clearing_rule(
        clearing_end
    ) or determine_clearing_rule(clearing_start)
    if not rule_target_or_origin:
        raise ValueError("player does not control either origin or target clearing")
    # update clearing of warriors
    for warrior in warriors:
        warrior.clearing = clearing_end
    Warrior.objects.bulk_update(warriors, ["clearing"])


@transaction.atomic
def remove_warriors_from_clearing(
    player: Player, clearing: Clearing, number: int, exact: bool = True
):
    """
    removes warriors from the given clearing
    if exact, will raise if not enough warriors to remove. otehrwise, will remove as many as possible
    """
    if exact and warrior_count_in_clearing(player, clearing) < number:
        raise ValueError("Not enough warriors in clearing to remove")
    Warrior.objects.filter(clearing=clearing, player=player)[:number].update(
        clearing=None
    )


@transaction.atomic
def craft_card(card_in_hand: HandEntry, crafting_pieces: list[Piece]):
    """crafts a card. If it is an item, scores the points and discards it
    If not, moves the card to the player's crafted card box
    """
    card: CardDetails = card_in_hand.card.enum.value
    if not card.craftable:
        raise ValueError("card is not craftable")
    item = card.item
    points = card.crafted_points
    crafting_cost = card.cost
    ## this first batch of logic can be a selector (can_craft)
    # check that card is an item card
    if item is not None:
        # check that item is still in the craftable pool
        if not CraftableItemEntry.objects.filter(item__item_type=item.value).exists():
            raise ValueError("item is not in the craftable pool")

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
    # check off requirements
    # sort so wild requirements are last, as they are the most flexible
    crafting_cost.sort(key=lambda x: 1 if x.suit == Suit.WILD else 0)
    for cost in crafting_cost:
        found = False
        for crafting_piece in crafting_pieces:
            assert isinstance(crafting_piece, CraftingPieceMixin)
            if isinstance(crafting_piece, Building):
                suit = crafting_piece.building_slot.clearing.suit
            elif isinstance(crafting_piece, (Token, Warrior)):
                suit = crafting_piece.clearing.suit
            else:
                raise ValueError("unknown piece type. need to add logic for this")

            if (cost == Suit.WILD or cost == suit) and not crafting_piece.crafted_with:
                crafting_piece.crafted_with = True
                # update here. cant bulk save since it may be different models
                crafting_piece.save()
                found = True
                break
        if not found:
            raise ValueError("could not find a piece to use." + f" cost: {cost}")
    ## this second batch belongs in a transaction

    if item is not None:
        # move item from pool to player's inventory
        item_from_pool = CraftableItemEntry.objects.filter(
            item__item_type=item.value
        ).first()
        assert item_from_pool is not None, "item not in pool"
        CraftedItemEntry(player=card_in_hand.player, item=item_from_pool).save()
        item_from_pool.delete()
        # update score
        card_in_hand.player.score += points
        card_in_hand.player.save()
        # discard card from player's hand
        discard_card_from_hand(card_in_hand.player, card_in_hand)
    else:  # not an item card
        # move card from player's hand to player's crafted card box
        CraftedCardEntry(player=card_in_hand.player, card=card_in_hand.card).save()
        # delete card from player's hand
        card_in_hand.delete()


@transaction.atomic
def next_players_turn(game: Game):
    """moves to the next player's turn"""
    player_count = Player.objects.filter(game=game).count()
    game.current_turn = (game.current_turn + 1) % player_count
    game.save()


@transaction.atomic
def raise_score(player: Player, amount: int):
    """
    raise a player's score, and check any relevant score related conditions, such as winning the game.
    """
    player.score += amount
    player.save()
    # TODO: check if player has won
    if player.score >= 30:
        raise ValueError("Player has won. TODO: implement winning logic")
