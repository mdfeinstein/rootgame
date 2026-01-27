from game.transactions.general import step_effect
from game.models.events.crafted_cards import SaboteursEvent
from django.db import transaction
from game.models.game_models import Player, CraftedCardEntry, DiscardPileEntry, Faction

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
    
    # resolve event
    event = SaboteursEvent.objects.filter(crafted_card_entry=saboteurs_entry).first()
    event.event.is_resolved = True
    event.event.save()

    

@transaction.atomic
def saboteurs_check(player: Player)->bool:
    """
    Checks if the player has Saboteurs and launches the event if so.
    Returns True if event launched, False otherwise
    """
    # 1. Check if player has Saboteurs
    saboteurs_entry = CraftedCardEntry.objects.filter(player=player, card__card_type=CardsEP.SABOTEURS.name, used=CraftedCardEntry.UsedChoice.UNUSED).first()
    has_saboteurs = saboteurs_entry is not None

    if has_saboteurs:
        # 2. Launch the event
        from game.models.events.crafted_cards import SaboteursEvent
        SaboteursEvent.create(saboteurs_entry)
    return has_saboteurs

@transaction.atomic
def saboteurs_skip(player: Player):
    """
    Player chooses to not use Saboteurs.
    Resolve event
    """
    saboteurs_entry = CraftedCardEntry.objects.filter(player=player, card__card_type=CardsEP.SABOTEURS.name).first()
    if saboteurs_entry is None:
         raise ValueError("Player does not have Saboteurs")
         
    # mark as used
    saboteurs_entry.used = CraftedCardEntry.UsedChoice.USED
    saboteurs_entry.save()
    
    event = SaboteursEvent.objects.filter(crafted_card_entry=saboteurs_entry).first()
    if event:
        event.event.is_resolved = True
        event.event.save()
    
    # continue phase step
    step_effect(player)

