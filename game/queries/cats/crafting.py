from game.game_data.cards.exiles_and_partisans import CardsEP
from game.game_data.general.game_enums import Suit
from game.models.cats.buildings import Workshop
from game.models.game_models import Player
from django.db.models import QuerySet


def get_unused_workshop_by_clearing_number(
    player: Player,
    clearing_number: int,
) -> Workshop | None:
    """returns an unused sawmill at the given clearing number"""
    workshop = Workshop.objects.filter(
        player=player, crafted_with=False, clearing__clearing_number=clearing_number
    ).first()
    return workshop


def get_all_unused_workshops(player: Player) -> QuerySet[Workshop]:
    """returns all unused sawmills on the board"""
    return Workshop.objects.filter(
        player=player, crafted_with=False, building_slot__isnull=False
    )


def validate_unused_workshops_by_clearing_number(
    player: Player, clearing_number: int, count: int
) -> list[Workshop]:
    """raises if not enough unused workshops at the given clearing number"""
    workshops = list(
        Workshop.objects.filter(
            player=player,
            building_slot__clearing__clearing_number=clearing_number,
            crafted_with=False,
        )
    )
    if len(workshops) < count:
        raise ValueError("Not enough unused workshops at that clearing")
    return workshops


def validate_crafting_pieces_satisfy_requirements(
    player: Player, card: CardsEP, workshops: list[Workshop]
) -> bool:
    """raises if pieces are a mismatch to the card's requirements
    return True if enough pieces to craft the card
    """
    suits_needed = card.value.cost
    satisfied = [False for _ in suits_needed]
    for workshop in workshops:
        if workshop.crafted_with:
            raise ValueError("A workshop is already used")
        workshop_suit = Suit(workshop.building_slot.clearing.suit)
        first_wild_idx: int | None = None
        for i, suit_needed in enumerate(suits_needed):
            if not satisfied[i] and suit_needed.value == workshop_suit.value:
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
