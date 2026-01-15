from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import CraftableItemEntry, Player, Suit
from game.models.wa.tokens import WASympathy


def is_able_to_be_crafted(player: Player, card: CardsEP) -> bool:
    """returns True if the player has enough crafting pieces to craft the card
    and card is craftable
    Just checks sympathy number, not specific crafting pieces
    """
    if not card.value.craftable:
        raise ValueError("Card is not craftable")
    card_item = card.value.item
    if card_item is not None:
        CraftableItemEntry.objects.filter(game=player.game, item=card_item).exists()
    sympathy_count = WASympathy.objects.filter(
        player=player, crafted_with=False, clearing__isnull=False
    ).count()
    return sympathy_count >= len(card.value.cost)


def validate_crafting_pieces_satisfy_requirements(
    player: Player, card: CardsEP, sympathies: list[WASympathy]
) -> bool:
    """raises if pieces are a mismatch to the card's requirements
    return True if enough pieces to craft the card
    """
    if not is_able_to_be_crafted(player, card):
        raise ValueError("Not enough crafting pieces available to craft this card")
    
    if len(sympathies) != len(set(sympathy.id for sympathy in sympathies)):
        raise ValueError("Cannot use the same crafting piece twice")

    suits_needed = card.value.cost
    satisfied = [False for _ in suits_needed]
    for sympathy in sympathies:
        sympathy_suit = Suit(sympathy.clearing.suit)

        # first try to find a matching suit
        match_found = False
        for i, suit_needed in enumerate(suits_needed):
            if not satisfied[i] and suit_needed.value == sympathy_suit.value:
                satisfied[i] = True
                match_found = True
                break
        
        # if not found, try to find a wild suit
        if not match_found:
            for i, suit_needed in enumerate(suits_needed):
                if not satisfied[i] and suit_needed.value == Suit.WILD.value:
                    satisfied[i] = True
                    match_found = True
                    break

        # if we looped thru and didnt find matching or wild, raise
        if not match_found:
            raise ValueError("No matching or wild suit found")

    return all(satisfied)
