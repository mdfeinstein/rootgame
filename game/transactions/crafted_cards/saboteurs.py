from django.db import transaction
from game.models.game_models import Player, CraftedCardEntry, DiscardPileEntry
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.general import validate_player_has_crafted_card
from game.queries.cards.active_effects import can_use_card

@transaction.atomic
def use_saboteurs(player: Player, target_crafted_card: CraftedCardEntry):
    """
    Implementation of the Saboteurs crafted card effect.
    At the start of Birdsong, may discard this card to discard another player's crafted card.
    """
    # 1. Validate player has Saboteurs
    saboteurs_entry = validate_player_has_crafted_card(player, CardsEP.SABOTEURS)
    
    # 2. Check if card can be used now (start of Birdsong)
    if not can_use_card(player, saboteurs_entry):
        raise ValueError("Saboteurs cannot be used right now. It must be at the start of your Birdsong.")
    
    # 3. Validation: Target card must be in the same game
    if player.game != target_crafted_card.player.game:
        raise ValueError("Target card is not in the same game.")
    
    # 4. Check if player owns the target card
    if target_crafted_card.player == player:
         raise ValueError("You cannot discard your own crafted card with Saboteurs.")

    # 5. Discard target card
    target_card = target_crafted_card.card
    target_crafted_card.delete()
    DiscardPileEntry.create_from_card(target_card)
    
    # 6. Discard Saboteurs
    saboteurs_card = saboteurs_entry.card
    saboteurs_entry.delete()
    DiscardPileEntry.create_from_card(saboteurs_card)
