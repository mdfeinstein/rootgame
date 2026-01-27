from game.transactions.general import step_effect
from game.models.events.crafted_cards import CharmOffensiveEvent
from django.db import transaction
from game.models.game_models import Player, CraftedCardEntry
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.general import validate_player_has_crafted_card
from game.queries.cards.active_effects import can_use_card
from game.transactions.general import draw_card_from_deck, raise_score

@transaction.atomic
def use_charm_offensive(player: Player, opponent: Player):
    """
    Implementation of the Charm Offensive crafted card effect.
    At the start of Evening, may draw a card and give an opponent 1 VP.
    """
    # 1. Validate player has the card
    crafted_card = validate_player_has_crafted_card(player, CardsEP.CHARM_OFFENSIVE)
    
    # 2. Check if card can be used now (start of Evening)
    if not can_use_card(player, crafted_card):
        raise ValueError("Charm Offensive cannot be used right now. It must be at the start of your Evening.")
    
    # 3. Validation: Opponent must be in the same game
    if player.game != opponent.game:
        raise ValueError("Opponent is not in the same game.")
    
    if player == opponent:
        raise ValueError("You cannot give yourself a point.")

    # 4. Draw a card for the player
    draw_card_from_deck(player)
    
    # 5. Raise score for the opponent
    raise_score(opponent, 1)
    
    # 6. Mark card as used
    crafted_card.used = CraftedCardEntry.UsedChoice.USED
    crafted_card.save()
    #resolve event
    event = CharmOffensiveEvent.objects.filter(crafted_card_entry=crafted_card).first()
    if event:
        event.event.is_resolved = True
        event.event.save()
    # resolve step_effect for beginning of evening
    step_effect(player)

@transaction.atomic
def check_charm_offensive(player: Player)->bool:
    """
    Checks if the Charm Offensive crafted card can be used.
    Launches event if it can, and returns True
    """
    try:
        crafted_card = validate_player_has_crafted_card(player, CardsEP.CHARM_OFFENSIVE)
    except ValueError:
        return False
    CharmOffensiveEvent.create(crafted_card)
    return True

@transaction.atomic
def skip_charm_offensive(player: Player):
    """ resolve the event and mark card as used """
    crafted_card = validate_player_has_crafted_card(player, CardsEP.CHARM_OFFENSIVE)
    crafted_card.used = CraftedCardEntry.UsedChoice.USED
    crafted_card.save()
    event = CharmOffensiveEvent.objects.filter(crafted_card_entry=crafted_card).first()
    if event:
        event.event.is_resolved = True
        event.event.save()
    # resolve step_effect for beginning of evening
    step_effect(player)