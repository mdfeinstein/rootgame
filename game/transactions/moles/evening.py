from typing import Literal
from django.db import transaction

from game.models.game_models import Player, HandEntry
from game.models.moles.turn import MoleEvening
from game.models.moles.buildings import Citadel, Market
from game.queries.moles.turn import validate_step
from game.errors import IllegalActionError


@transaction.atomic
def process_revealed_cards(player: Player):
    """Process revealed cards - move them to hand or discard.

    Currently a placeholder for future card effect processing.
    """
    validate_step(player, MoleEvening.MoleEveningSteps.PROCESS_REVEALED_CARDS)

    from game.transactions.moles.turn import next_step

    next_step(player)


@transaction.atomic
def craft(player: Player, building: Literal["citadel", "market"]):
    """Craft an item by spending a building.

    Args:
        player: The Moles player
        building: "citadel" or "market"

    Raises:
        IllegalActionError if building not available or already used this turn
    """
    validate_step(player, MoleEvening.MoleEveningSteps.CRAFT)

    # Get available building
    if building == "citadel":
        building_instance = Citadel.objects.filter(
            player=player, building_slot__isnull=False, crafted_with=False
        ).first()
        if building_instance is None:
            raise IllegalActionError("No available citadels to craft with")
    else:  # building == "market"
        building_instance = Market.objects.filter(
            player=player, building_slot__isnull=False, crafted_with=False
        ).first()
        if building_instance is None:
            raise IllegalActionError("No available markets to craft with")

    # Mark building as used for crafting this turn
    building_instance.crafted_with = True
    building_instance.save()


@transaction.atomic
def draw(player: Player, count: int = 1):
    """Draw cards from deck.

    Args:
        player: The Moles player
        count: Number of cards to draw (default 1)

    Raises:
        IllegalActionError if invalid count
    """
    validate_step(player, MoleEvening.MoleEveningSteps.DRAW)

    if count < 1:
        raise IllegalActionError("Must draw at least 1 card")

    from game.queries.general import draw_cards

    draw_cards(player, count)

    # Update cards drawn counter
    phase = MoleEvening.objects.get(turn__player=player, turn__turn_number=player.turn_number)
    phase.cards_drawn += count
    phase.save()


@transaction.atomic
def discard(player: Player, card_entry: HandEntry):
    """Discard a card from hand.

    Args:
        player: The Moles player
        card_entry: The HandEntry to discard

    Raises:
        IllegalActionError if card not in player's hand
    """
    validate_step(player, MoleEvening.MoleEveningSteps.DISCARD)

    if card_entry.player != player:
        raise IllegalActionError("Card not in this player's hand")

    from game.transactions.general import discard_card_from_hand

    discard_card_from_hand(player, card_entry)
