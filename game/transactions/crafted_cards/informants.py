from django.db import transaction
from rest_framework.exceptions import ValidationError
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.events.event import Event, EventType
from game.models.events.crafted_cards import InformantsEvent
from game.models.game_models import CraftedCardEntry, DiscardPileEntry, HandEntry, Card

@transaction.atomic
def use_informants(crafted_card_entry: CraftedCardEntry, ambush_card_in_discard: DiscardPileEntry):
    if crafted_card_entry.card.card_type != CardsEP.INFORMANTS.name:
         raise ValidationError({"detail": "Card is not Informants."})
    
    if crafted_card_entry.used != CraftedCardEntry.UsedChoice.UNUSED:
        raise ValidationError({"detail": "Card has already been used this turn."})

    # Validate ambush card
    card_data = CardsEP[ambush_card_in_discard.card.card_type].value
    if not card_data.ambush:
        raise ValidationError({"detail": "Selected card is not an ambush card."})

    player = crafted_card_entry.player
    game = player.game

    # Move card from discard pile to hand
    HandEntry.objects.create(player=player, card=ambush_card_in_discard.card)
    ambush_card_in_discard.delete()

    # Mark as used
    crafted_card_entry.used = CraftedCardEntry.UsedChoice.USED
    crafted_card_entry.save()

    # Resolve event
    informants_event = InformantsEvent.objects.filter(crafted_card_entry=crafted_card_entry, event__is_resolved=False).first()
    if informants_event:
        informants_event.event.is_resolved = True
        informants_event.event.save()

@transaction.atomic
def skip_informants(crafted_card_entry: CraftedCardEntry):
    if crafted_card_entry.card.card_type != CardsEP.INFORMANTS.name:
         raise ValidationError({"detail": "Card is not Informants."})

    # Mark as used
    crafted_card_entry.used = CraftedCardEntry.UsedChoice.USED
    crafted_card_entry.save()

    # Resolve event
    informants_event = InformantsEvent.objects.filter(crafted_card_entry=crafted_card_entry, event__is_resolved=False).first()
    if informants_event:
        informants_event.event.is_resolved = True
        informants_event.event.save()
