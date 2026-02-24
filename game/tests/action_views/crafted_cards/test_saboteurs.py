from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, CraftedCardEntry, Card, DiscardPileEntry
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.events.crafted_cards import SaboteursEvent

class SaboteursViewTestCase(TestCase):
    def setUp(self):
        # Create game with Cats and Birds
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Setup passwords for client login
        self.birds_player.user.set_password("password")
        self.birds_player.user.save()
        
        self.birds_client = RootGameClient(self.birds_player.user.username, "password", self.game.id)
        
        # Give Birds Saboteurs card
        self.card = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name)
        self.entry = CraftedCardEntryFactory(player=self.birds_player, card=self.card, used=CraftedCardEntry.UsedChoice.UNUSED)

        # Give Cats a crafted card to sabotage
        self.cats_card = CardFactory(game=self.game, card_type=CardsEP.SOUP_KITCHENS.name)
        self.cats_entry = CraftedCardEntryFactory(player=self.cats_player, card=self.cats_card)

        # Set Birds turn and phase to Birdsong
        from game.models.birds.turn import BirdTurn, BirdBirdsong
        self.game.current_turn = 1
        self.game.save()
        if not BirdTurn.objects.filter(player=self.birds_player).exists():
            BirdTurn.create_turn(self.birds_player)
            
        turn = BirdTurn.objects.filter(player=self.birds_player).order_by("-turn_number").first()
        birdsong = BirdBirdsong.objects.get(turn=turn)
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.EMERGENCY_DRAWING
        birdsong.save()

        # Create the event
        SaboteursEvent.create(self.entry)

    def test_saboteurs_flow(self):
        """Test Saboteurs flow."""
        self.birds_client.base_route = "/api/action/card/saboteurs/"
        
        # 1. Initial GET -> pick-faction
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.birds_client.step = response.data
        self.assertEqual(response.data["name"], "pick-faction")
        
        # 2. SUBMIT Cats -> pick-card
        response = self.birds_client.submit_action({"faction": Faction.CATS.value})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-card")
        
        # 3. SUBMIT Soup Kitchens -> completed
        response = self.birds_client.submit_action({"card": CardsEP.SOUP_KITCHENS.name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify Cat card sabotaged (entry deleted, card in discard pile)
        self.assertFalse(CraftedCardEntry.objects.filter(pk=self.cats_entry.pk).exists())
        self.assertTrue(DiscardPileEntry.objects.filter(game=self.game, card=self.cats_card).exists())
        # Verify Saboteurs card deleted and in discard pile
        self.assertFalse(CraftedCardEntry.objects.filter(pk=self.entry.pk).exists())
        self.assertTrue(DiscardPileEntry.objects.filter(game=self.game, card=self.card).exists())

    def test_saboteurs_skip(self):
        """Test skipping Saboteurs."""
        self.birds_client.base_route = "/api/action/card/saboteurs/"
        
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.birds_client.step = response.data
        response = self.birds_client.submit_action({"faction": "skip"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify cards still there
        self.assertTrue(CraftedCardEntry.objects.filter(pk=self.cats_entry.pk).exists())
        self.assertTrue(CraftedCardEntry.objects.filter(pk=self.entry.pk).exists())
