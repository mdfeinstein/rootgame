from django.test import TestCase
from game.models.game_models import Faction, CraftedCardEntry, DiscardPileEntry, HandEntry
from game.models.events.event import Event, EventType
from game.models.events.crafted_cards import InformantsEvent
from game.transactions.crafted_cards.informants import use_informants, skip_informants
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.tests.my_factories import PlayerFactory, CardFactory, CraftedCardEntryFactory, DiscardPileEntryFactory
from rest_framework.exceptions import ValidationError

class InformantsTransactionTests(TestCase):
    def test_use_informants_success(self):
        player = PlayerFactory(faction=Faction.CATS)
        game = player.game
        
        # Setup card
        informants_card = CardFactory(game=game, card_type=CardsEP.INFORMANTS.name)
        crafted_card = CraftedCardEntryFactory(player=player, card=informants_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Setup ambush card in discard pile
        ambush_card = CardFactory(game=game, card_type=CardsEP.AMBUSH_RED.name)
        discard_entry = DiscardPileEntryFactory(game=game, card=ambush_card)
        
        # Setup event
        event = Event.objects.create(game=game, type=EventType.INFORMANTS)
        InformantsEvent.objects.create(event=event, crafted_card_entry=crafted_card)
        
        # Use informants
        use_informants(crafted_card, discard_entry)
        
        # Verify
        assert HandEntry.objects.filter(player=player, card=ambush_card).exists()
        assert not DiscardPileEntry.objects.filter(id=discard_entry.id).exists()
        crafted_card.refresh_from_db()
        assert crafted_card.used == CraftedCardEntry.UsedChoice.USED
        event.refresh_from_db()
        assert event.is_resolved == True

    def test_skip_informants_success(self):
        player = PlayerFactory(faction=Faction.CATS)
        game = player.game
        
        informants_card = CardFactory(game=game, card_type=CardsEP.INFORMANTS.name)
        crafted_card = CraftedCardEntryFactory(player=player, card=informants_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        event = Event.objects.create(game=game, type=EventType.INFORMANTS)
        InformantsEvent.objects.create(event=event, crafted_card_entry=crafted_card)
        
        skip_informants(crafted_card)
        
        crafted_card.refresh_from_db()
        assert crafted_card.used == CraftedCardEntry.UsedChoice.USED
        event.refresh_from_db()
        assert event.is_resolved == True

    def test_use_informants_fail_not_ambush(self):
        player = PlayerFactory(faction=Faction.CATS)
        game = player.game
        
        informants_card = CardFactory(game=game, card_type=CardsEP.INFORMANTS.name)
        crafted_card = CraftedCardEntryFactory(player=player, card=informants_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Non-ambush card
        not_ambush_card = CardFactory(game=game, card_type=CardsEP.SABOTEURS.name)
        discard_entry = DiscardPileEntryFactory(game=game, card=not_ambush_card)
        
        with self.assertRaises(ValidationError) as cm:
            use_informants(crafted_card, discard_entry)
        self.assertIn("not an ambush card", str(cm.exception.detail))
