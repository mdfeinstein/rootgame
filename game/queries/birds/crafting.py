from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.buildings import BirdRoost
from game.models.game_models import Player, Suit
from django.db.models import QuerySet


def get_all_unused_roosts(player: Player) -> QuerySet[BirdRoost]:
    """returns all unused sawmills on the board"""
    return BirdRoost.objects.filter(
        player=player, crafted_with=False, building_slot__isnull=False
    )


def is_able_to_be_crafted(player: Player, card: CardsEP) -> bool:
    """returns True if the player has enough crafting pieces to craft the card
    For now, will just check roost count against card requirements. wont check specific reqs yet
    """
    if not card.value.craftable:
        raise ValueError("Card is not craftable")
    roost_count = get_all_unused_roosts(player).count()
    return roost_count < len(card.value.cost)


def validate_crafting_pieces_satisfy_requirements(
    player: Player, card: CardsEP, roosts: list[BirdRoost]
) -> bool:
    """raises if pieces are a mismatch to the card's requirements
    return True if enough pieces to craft the card
    """
    if not is_able_to_be_crafted(player, card):
        raise ValueError("Not enough crafting pieces available to craft this card")
    suits_needed = card.value.cost
    satisfied = [False for _ in suits_needed]
    for roost in roosts:
        roost_suit = Suit(roost.building_slot.clearing.suit)
        print(roost_suit)
        first_wild_idx: int | None = None
        for i, suit_needed in enumerate(suits_needed):
            if not satisfied[i] and suit_needed.value == roost_suit.value:
                print(f"satisfied suit {suit_needed.value}")
                satisfied[i] = True
                break
            elif (
                not satisfied[i]
                and suit_needed.value == Suit.WILD.value
                and first_wild_idx is None
            ):
                first_wild_idx = i
            # if we looped thru and didnt find matching or wild, raise
            if first_wild_idx is None:
                raise ValueError("No matching or wild suit found")
            else:
                # use the first wild
                satisfied[first_wild_idx] = True

    return all(satisfied)
