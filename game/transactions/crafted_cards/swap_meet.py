from game.queries.general import validate_player_has_card_in_hand
from game.queries.general import validate_player_has_crafted_card
from random import choice
from django.db import transaction
from game.models import HandEntry, Card, CraftedCardEntry
from game.models.events.crafted_cards import SwapMeetEvent
from game.queries.cards.active_effects import can_use_card
from game.game_data.cards.exiles_and_partisans import CardsEP

@transaction.atomic
def swap_meet_take_card(player, target_player):
    """
    Takes a random card from target_player's hand and adds it to player's hand.
    Mark Swap Meet card as used.
    """
    if player == target_player:
        raise ValueError("Cannot take card from yourself")
    if player.game != target_player.game:
        raise ValueError("Players must be in the same game")
    crafted_card = validate_player_has_crafted_card(player, CardsEP.SWAP_MEET)
    
    if not can_use_card(player, crafted_card):
        raise ValueError("Swap Meet cannot be used right now")

    target_hand = HandEntry.objects.filter(player=target_player)
    if not target_hand.exists():
        raise ValueError("Target player has no cards in hand")

    # Pick a random card
    taken_hand_entry = choice(list(target_hand))
    taken_card = taken_hand_entry.card

    # Move card
    taken_hand_entry.player = player
    taken_hand_entry.save()

    # Create event
    SwapMeetEvent.create(taking_player=player, taken_from_player=target_player)

    # Mark card as used
    crafted_card.used = CraftedCardEntry.UsedChoice.USED
    crafted_card.save()
    
    return taken_card

@transaction.atomic
def swap_meet_give_card(swap_meet_event: SwapMeetEvent, card_to_give: CardsEP):
    """
    Gives a card from taking_player's hand to taken_from_player.
    Resolves the event.
    """
    taking_player = swap_meet_event.taking_player
    taken_from_player = swap_meet_event.taken_from_player

    hand_entry = validate_player_has_card_in_hand(taking_player, card_to_give)
    # Move card
    hand_entry.player = taken_from_player
    hand_entry.save()

    # Resolve event
    swap_meet_event.event.is_resolved = True
    swap_meet_event.event.save()
