from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Player, Suit
from game.models.moles.buildings import Citadel, Market
from game.errors import IllegalActionError


def get_all_unused_mole_buildings(player: Player) -> list:
    """Returns all citadels and markets on map that haven't been crafted with this turn."""
    citadels = list(
        Citadel.objects.filter(player=player, building_slot__isnull=False, crafted_with=False)
    )
    markets = list(
        Market.objects.filter(player=player, building_slot__isnull=False, crafted_with=False)
    )
    return citadels + markets


def validate_crafting_pieces_satisfy_requirements(
    player: Player, card: CardsEP, buildings: list
) -> bool:
    """Validates that the given buildings satisfy the card's crafting cost.

    Suit derived from building.building_slot.clearing.suit.
    Raises IllegalActionError if pieces don't satisfy card requirements.
    """
    suits_needed = card.value.cost
    if len(buildings) != len(suits_needed):
        raise IllegalActionError(
            f"Card requires {len(suits_needed)} crafting pieces, got {len(buildings)}"
        )

    if len(buildings) != len(set(b.id for b in buildings)):
        raise IllegalActionError("Duplicate crafting pieces provided")

    satisfied = [False for _ in suits_needed]
    for building in buildings:
        if building.crafted_with:
            raise IllegalActionError("A building has already been used for crafting this turn")
        building_suit = Suit(building.building_slot.clearing.suit)
        matched = False
        first_wild_idx = None
        for i, suit_needed in enumerate(suits_needed):
            if satisfied[i]:
                continue
            if suit_needed.value == building_suit.value:
                satisfied[i] = True
                matched = True
                break
            elif suit_needed.value == Suit.WILD.value and first_wild_idx is None:
                first_wild_idx = i
        if not matched:
            if first_wild_idx is None:
                raise IllegalActionError(
                    f"Building in {building_suit} clearing does not satisfy any remaining requirement"
                )
            satisfied[first_wild_idx] = True

    return True
