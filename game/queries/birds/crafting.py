from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.buildings import BirdRoost
from game.models.game_models import CraftableItemEntry, Player, Suit
from django.db.models import QuerySet


def get_all_unused_roosts(player: Player) -> QuerySet[BirdRoost]:
    """returns all unused roosts on the board"""
    return BirdRoost.objects.filter(
        player=player, crafted_with=False, building_slot__isnull=False
    )


def is_able_to_be_crafted(player: Player, card: CardsEP) -> bool:
    """returns True if the player has enough crafting pieces to craft the card
    For now, will just check roost count against card requirements. wont check specific reqs yet
    """
    if not card.value.craftable:
        raise ValueError("Card is not craftable")
    card_item = card.value.item
    if card_item is not None:
        CraftableItemEntry.objects.filter(game=player.game, item=card_item).exists()
    roost_count = get_all_unused_roosts(player).count()
    return roost_count >= len(card.value.cost)


def validate_crafting_pieces_satisfy_requirements(
    player: Player, card: CardsEP, roosts: list[BirdRoost]
) -> bool:
    """raises if pieces are a mismatch to the card's requirements
    return True if enough pieces to craft the card
    """
    if not is_able_to_be_crafted(player, card):
        raise ValueError("Not enough crafting pieces available to craft this card")
    
    if len(roosts) != len(set(roost.id for roost in roosts)):
        raise ValueError("Cannot use the same crafting piece twice")

    suits_needed = card.value.cost
    satisfied = [False for _ in suits_needed]
    for roost in roosts:
        if roost.crafted_with:
            raise ValueError("Roost already crafted with")
        roost_suit = Suit(roost.building_slot.clearing.suit)

        # first try to find a matching suit
        match_found = False
        for i, suit_needed in enumerate(suits_needed):
            if not satisfied[i] and suit_needed.value == roost_suit.value:
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
