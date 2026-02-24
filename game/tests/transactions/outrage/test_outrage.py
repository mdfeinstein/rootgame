from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, Card, HandEntry, Suit, Game
from game.models.events.wa import OutrageEvent
from game.models.wa.tokens import WASympathy
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, WarriorFactory
from game.transactions.removal import player_removes_token
from game.transactions.general import move_warriors
from game.transactions.wa import pay_outrage
from game.game_data.cards.exiles_and_partisans import CardsEP

class OutrageTests(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.WOODLAND_ALLIANCE])
        self.cats = self.game.players.get(faction=Faction.CATS)
        self.wa = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)
        
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1) # Fox (Red)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=9) # Mouse (Orange)
        
        # Clear pieces to ensure clean state
        Warrior.objects.all().delete()
        WASympathy.objects.all().delete()

    def test_outrage_token_removal_with_card(self):
        # Setup: WA sympathy in C1 (Fox/Red)
        sympathy = WASympathy.objects.create(player=self.wa, clearing=self.c1)
        
        # Cats have a Fox card
        fox_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.cats, card=fox_card)
        
        # Cats remove sympathy
        player_removes_token(self.game, sympathy, self.cats)
        
        # Outrage event should be created and NOT resolved
        outrage_event = OutrageEvent.objects.get(outraged_player=self.wa, outrageous_player=self.cats)
        self.assertFalse(outrage_event.event.is_resolved)
        self.assertEqual(outrage_event.suit, self.c1.suit)
        
        # Cats pay outrage
        fox_card_enum = CardsEP[fox_card.card_type]
        pay_outrage(outrage_event, fox_card_enum)
        
        # Verify card moved to supporters
        from game.models.wa.player import SupporterStackEntry
        self.assertTrue(SupporterStackEntry.objects.filter(player=self.wa, card=fox_card).exists())
        self.assertFalse(HandEntry.objects.filter(player=self.cats, card=fox_card).exists())
        
        outrage_event.event.refresh_from_db()
        self.assertTrue(outrage_event.event.is_resolved)

    def test_outrage_move_into_with_card(self):
        # Setup: WA sympathy in C2 (Mouse)
        WASympathy.objects.create(player=self.wa, clearing=self.c2)
        
        # Cats in C1 (Fox)
        WarriorFactory.create_batch(2, player=self.cats, clearing=self.c1)
        
        # Cats have a Mouse card
        mouse_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_ORANGE.name)
        HandEntry.objects.create(player=self.cats, card=mouse_card)
        
        # Cats move into C2
        move_warriors(self.cats, self.c1, self.c2, 1)
        
        # Outrage triggered
        outrage_event = OutrageEvent.objects.get(outraged_player=self.wa, outrageous_player=self.cats)
        self.assertFalse(outrage_event.event.is_resolved)
        
        # Pay
        mouse_card_enum = CardsEP[mouse_card.card_type]
        pay_outrage(outrage_event, mouse_card_enum)
        
        self.assertTrue(outrage_event.event.is_resolved)

    def test_outrage_no_card_auto_resolution(self):
        # Setup: WA sympathy in C1
        sympathy = WASympathy.objects.create(player=self.wa, clearing=self.c1)
        
        # Cats have NO matching cards
        Card.objects.all().delete() # Empty deck/hands for local test
        from game.models import DeckEntry
        deck_card = CardFactory(game=self.game)
        DeckEntry.objects.create(game=self.game, card=deck_card, spot=0)
        
        # Cats remove sympathy
        player_removes_token(self.game, sympathy, self.cats)
        
        # Should auto-resolve by drawing to supporters
        outrage_event = OutrageEvent.objects.get(outraged_player=self.wa, outrageous_player=self.cats)
        self.assertTrue(outrage_event.event.is_resolved)
        self.assertTrue(outrage_event.card_given)
        
        from game.models.wa.player import SupporterStackEntry
        self.assertTrue(SupporterStackEntry.objects.filter(player=self.wa).exists())
