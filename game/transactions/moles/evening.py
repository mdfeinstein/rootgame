from django.db import transaction

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Player, HandEntry, RevealedCardEntry
from game.models.enums import Suit, Faction
from game.models.moles.turn import MoleEvening
from game.models.moles.buildings import Market
from game.queries.moles.turn import validate_step
from game.queries.moles.evening import validate_discard_card
from game.queries.moles.crafting import validate_crafting_pieces_satisfy_requirements
from game.queries.general import validate_player_has_card_in_hand, get_player_hand_size
from game.errors import UnavailableActionError
from game.transactions.general import (
    draw_card_from_deck_to_hand,
    discard_card_from_hand,
)


@transaction.atomic
def process_revealed_cards(player: Player):
    """Process revealed cards at start of evening.

    Wild (Bird suit) cards go to discard; all others return to hand.
    Auto-called from step_effect.
    """
    validate_step(player, MoleEvening.MoleEveningSteps.PROCESS_REVEALED_CARDS)

    revealed = RevealedCardEntry.objects.filter(player=player, returned_to_hand=False)
    for entry in revealed:
        card_suit = entry.card.enum.value.suit
        if card_suit == Suit.WILD:
            entry.revealed_to_discard()
        else:
            entry.revealed_to_hand()

    from game.transactions.moles.turn import next_step
    next_step(player)


@transaction.atomic
def craft_card(player: Player, card: CardsEP, buildings: list):
    """Craft a card using citadels and/or markets as crafting pieces.

    Args:
        player: The Moles player
        card: The card to craft from hand
        buildings: List of Citadel/Market instances to use as crafting pieces

    Raises:
        IllegalActionError if card not in hand, buildings don't satisfy cost, etc.
    """
    validate_step(player, MoleEvening.MoleEveningSteps.CRAFT)

    card_in_hand = validate_player_has_card_in_hand(player, card)
    validate_crafting_pieces_satisfy_requirements(player, card, buildings)

    from game.transactions.general import craft_card as general_craft_card
    general_craft_card(card_in_hand, buildings)


@transaction.atomic
def end_crafting(player: Player):
    """End the Craft step and advance to the next step.

    Validates that it's the correct phase/step and the player is Moles.
    """
    validate_step(player, MoleEvening.MoleEveningSteps.CRAFT)
    if player.faction != Faction.MOLES:
        raise UnavailableActionError("Not a Moles player")

    from game.transactions.moles.turn import next_step
    next_step(player)


@transaction.atomic
def draw_cards(player: Player):
    """Draw cards at end of evening: 1 base + 1 per market on the board.

    Auto-called from step_effect when entering DRAW step.
    """
    validate_step(player, MoleEvening.MoleEveningSteps.DRAW)

    markets_on_map = Market.objects.filter(player=player, building_slot__isnull=False).count()
    count = 1 + markets_on_map

    for _ in range(count):
        draw_card_from_deck_to_hand(player)

    from game.transactions.moles.turn import next_step
    next_step(player)


@transaction.atomic
def discard_card(player: Player, card_entry: HandEntry):
    """Discard one card from hand during the Discard step.

    Raises UnavailableActionError if hand is already at or below 5 cards.
    Advances to next step if hand reaches 5 after discarding.
    """
    validate_step(player, MoleEvening.MoleEveningSteps.DISCARD)

    if get_player_hand_size(player) <= 5:
        raise UnavailableActionError("Hand is already at or below 5 cards")

    validate_discard_card(player, card_entry)
    discard_card_from_hand(player, card_entry)

    if get_player_hand_size(player) <= 5:
        from game.transactions.moles.turn import next_step
        next_step(player)


@transaction.atomic
def end_discard(player: Player):
    """End the Discard step and advance to the next step.

    Validates that it's the correct phase/step and the player is Moles.
    """
    validate_step(player, MoleEvening.MoleEveningSteps.DISCARD)
    if player.faction != Faction.MOLES:
        raise UnavailableActionError("Not a Moles player")

    from game.transactions.moles.turn import next_step
    next_step(player)
