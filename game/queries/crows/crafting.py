from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import CraftableItemEntry, Player, Suit
from game.models.crows.tokens import PlotToken


def is_able_to_be_crafted(player: Player, card: CardsEP) -> bool:
    """returns True if the player has enough crafting pieces to craft the card
    and card is craftable
    Just checks plot token number, not specific crafting pieces
    """
    if not card.value.craftable:
        raise ValueError("Card is not craftable")
    card_item = card.value.item
    if card_item is not None:
        if not CraftableItemEntry.objects.filter(game=player.game, item__item_type=card_item.value).exists():
           return False
    # Crows craft with plot tokens on the board (face up or face down)
    plots = PlotToken.objects.filter(
        player=player, crafted_with=False, clearing__isnull=False
    )
    plot_count = plots.count()
    return plot_count >= len(card.value.cost)


def validate_crafting_pieces_satisfy_requirements(
    player: Player, card: CardsEP, plot_tokens: list[PlotToken]
) -> bool:
    """raises if pieces are a mismatch to the card's requirements
    return True if enough pieces to craft the card
    """
    if not is_able_to_be_crafted(player, card):
        raise ValueError("Not enough crafting pieces available to craft this card")
    
    if len(plot_tokens) != len(set(token.id for token in plot_tokens)):
        raise ValueError("Cannot use the same crafting piece twice")
        
    for token in plot_tokens:
        if token.clearing is None:
            raise ValueError("Cannot craft using plot tokens in reserve")

    suits_needed = card.value.cost
    satisfied = [False for _ in suits_needed]
    for token in plot_tokens:
        token_suit = Suit(token.clearing.suit)

        # first try to find a matching suit
        match_found = False
        for i, suit_needed in enumerate(suits_needed):
            if not satisfied[i] and suit_needed.value == token_suit.value:
                satisfied[i] = True
                match_found = True
                break
        
        # if not found, try to find a wild suit
        if not match_found:
            for i, suit_needed in enumerate(suits_needed):
                # Wild cards in hand can be used as any suit, but a wild clearing is not a thing unless special board.
                if not satisfied[i] and suit_needed.value == Suit.WILD.value:
                    satisfied[i] = True
                    match_found = True
                    break

        # if we looped thru and didnt find matching or wild, raise
        if not match_found:
            raise ValueError(f"Plot token in {token_suit.name} clearing does not match any required suit.")

    return all(satisfied)
