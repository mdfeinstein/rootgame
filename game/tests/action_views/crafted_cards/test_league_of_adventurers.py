from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, CraftedCardEntry, Clearing, Warrior, CraftedItemEntry, Item
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory, ItemFactory, CraftedItemEntryFactory
from game.game_data.cards.exiles_and_partisans import CardsEP

class LeagueOfAdventurersViewTestCase(TestCase):
    def setUp(self):
        # Create game with Cats and Birds
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Setup passwords for client login
        self.birds_player.user.set_password("password")
        self.birds_player.user.save()
        
        self.birds_client = RootGameClient(self.birds_player.user.username, "password", self.game.id)
        
        # Give Birds League card
        self.card = CardFactory(game=self.game, card_type=CardsEP.LEAGUE_OF_ADVENTURERS.name)
        self.entry = CraftedCardEntryFactory(player=self.birds_player, card=self.card, used=CraftedCardEntry.UsedChoice.UNUSED)

        # Give Birds an item
        self.item = ItemFactory(game=self.game)
        self.item_entry = CraftedItemEntryFactory(player=self.birds_player, item=self.item, exhausted=False)

        # Place some warriors
        self.clearing1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.clearing2 = Clearing.objects.get(game=self.game, clearing_number=2)
        Warrior.objects.create(player=self.birds_player, clearing=self.clearing1)
        
        # Ensure they are adjacent
        if self.clearing2 not in self.clearing1.connected_clearings.all():
            self.clearing1.connected_clearings.add(self.clearing2)

        # Set Birds turn and phase to Daylight
        from game.models.birds.turn import BirdTurn, BirdBirdsong, BirdDaylight
        self.game.current_turn = 1
        self.game.save()
        if not BirdTurn.objects.filter(player=self.birds_player).exists():
            BirdTurn.create_turn(self.birds_player)
            
        turn = BirdTurn.objects.filter(player=self.birds_player).order_by("-turn_number").first()
        birdsong = BirdBirdsong.objects.get(turn=turn)
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()
        
        daylight = BirdDaylight.objects.get(turn=turn)
        daylight.step = BirdDaylight.BirdDaylightSteps.CRAFTING
        daylight.save()

    def test_league_move_flow(self):
        """Test League of Adventurers move flow."""
        self.birds_client.base_route = "/api/action/card/league-of-adventurers/"
        
        # 1. Initial GET -> pick-item
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.birds_client.step = response.data
        self.assertEqual(response.data["name"], "pick-item")
        
        # 2. SUBMIT item -> pick-action
        response = self.birds_client.submit_action({"select": str(self.item_entry.id)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-action")
        
        # 3. SUBMIT "move" -> pick-origin
        response = self.birds_client.submit_action({"choice": "move"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-origin")
        
        # 4. SUBMIT origin -> pick-destination
        response = self.birds_client.submit_action({"clearing_number": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-destination")
        
        # 5. SUBMIT destination -> pick-count
        response = self.birds_client.submit_action({"clearing_number": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-count")
        
        # 6. SUBMIT count -> completed
        response = self.birds_client.submit_action({"number": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify warrior moved
        self.assertEqual(Warrior.objects.filter(player=self.birds_player, clearing=self.clearing2).count(), 1)
        # Verify item exhausted
        self.item_entry.refresh_from_db()
        self.assertTrue(self.item_entry.exhausted)
