from typing import Literal

from game.models.game_models import Player, HandEntry
from game.models.moles.buildings import Citadel, Market
from game.errors import IllegalActionError


def validate_craft_building(player: Player, building: Literal["citadel", "market"]) -> Citadel | Market:
    """Validate building is available for crafting.

    Args:
        player: The Moles player
        building: "citadel" or "market"

    Returns:
        The building instance available for crafting

    Raises:
        IllegalActionError if building not available or already used
    """
    if building == "citadel":
        building_instance = Citadel.objects.filter(
            player=player, building_slot__isnull=False, crafted_with=False
        ).first()
        if building_instance is None:
            raise IllegalActionError("No available citadels to craft with")
        return building_instance
    else:  # building == "market"
        building_instance = Market.objects.filter(
            player=player, building_slot__isnull=False, crafted_with=False
        ).first()
        if building_instance is None:
            raise IllegalActionError("No available markets to craft with")
        return building_instance


def validate_discard_card(player: Player, card_entry: HandEntry) -> HandEntry:
    """Validate card is in player's hand and can be discarded.

    Args:
        player: The Moles player
        card_entry: The HandEntry to validate

    Returns:
        The card entry

    Raises:
        IllegalActionError if card not in hand
    """
    if card_entry.player != player:
        raise IllegalActionError("Card not in this player's hand")

    if card_entry.hand is None:
        raise IllegalActionError("Card is not in hand")

    return card_entry
