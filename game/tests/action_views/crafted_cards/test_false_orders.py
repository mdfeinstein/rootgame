from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, CraftedCardEntry, Clearing, Warrior
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory
from game.game_data.cards.exiles_and_partisans import CardsEP

class FalseOrdersViewTestCase(TestCase):
    def setUp(self):
        # Create game with Cats and Birds
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Setup passwords for client login
        self.birds_player.user.set_password("password")
        self.birds_player.user.save()
        
        self.birds_client = RootGameClient(self.birds_player.user.username, "password", self.game.id)
        
        # Give Birds False Orders card
        self.card = CardFactory(game=self.game, card_type=CardsEP.FALSE_ORDERS.name)
        self.entry = CraftedCardEntryFactory(player=self.birds_player, card=self.card, used=CraftedCardEntry.UsedChoice.UNUSED)

        # Place some warriors for move
        self.clearing1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.clearing2 = Clearing.objects.get(game=self.game, clearing_number=2)
        Warrior.objects.create(player=self.cats_player, clearing=self.clearing1)
        
        # Ensure they are adjacent
        if self.clearing2 not in self.clearing1.connected_clearings.all():
            self.clearing1.connected_clearings.add(self.clearing2)

        # Set Birds turn and phase to Birdsong
        from game.models.birds.turn import BirdTurn, BirdBirdsong
        self.game.current_turn = 1
        self.game.save()
        if not BirdTurn.objects.filter(player=self.birds_player).exists():
            BirdTurn.create_turn(self.birds_player)
        
        turn = BirdTurn.objects.filter(player=self.birds_player).order_by("-turn_number").first()
        birdsong = BirdBirdsong.objects.get(turn=turn)
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE
        birdsong.save()

    def test_false_orders_flow(self):
        """Test False Orders flow."""
        self.birds_client.base_route = "/api/action/card/false-orders/"
        
        # 1. Initial GET -> pick-origin
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.birds_client.step = response.data
        self.assertEqual(response.data["name"], "pick-origin")
        
        # 2. SUBMIT origin -> pick-faction
        # Client needs to send 'select' because that's what payload_details says
        response = self.birds_client.submit_action({"select": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-faction")
        
        # 3. SUBMIT faction -> pick-destination
        response = self.birds_client.submit_action({"faction": "ca"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-destination")
        
        # 4. SUBMIT destination -> completed
        response = self.birds_client.submit_action({"clearing_number": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify Cats warriors moved
        self.assertEqual(Warrior.objects.filter(player=self.cats_player, clearing=self.clearing2).count(), 1)
        self.assertEqual(Warrior.objects.filter(player=self.cats_player, clearing=self.clearing1).count(), 0)

    def test_false_orders_skip(self):
        """Test skipping False Orders."""
        self.birds_client.base_route = "/api/action/card/false-orders/"
        
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.birds_client.step = response.data
        response = self.birds_client.submit_action({"select": "skip"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify card NOT marked as used (it's only discarded on use)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.used, CraftedCardEntry.UsedChoice.UNUSED)
