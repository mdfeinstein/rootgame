from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, CraftedCardEntry, Clearing, Warrior, Card, HandEntry
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory, HandEntryFactory
from game.game_data.cards.exiles_and_partisans import CardsEP

class PropagandaBureauViewTestCase(TestCase):
    def setUp(self):
        # Create game with Cats and Birds
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Setup passwords for client login
        self.birds_player.user.set_password("password")
        self.birds_player.user.save()
        
        self.birds_client = RootGameClient(self.birds_player.user.username, "password", self.game.id)
        
        # Give Birds Propaganda Bureau card
        self.card = CardFactory(game=self.game, card_type=CardsEP.PROPAGANDA_BUREAU.name)
        self.entry = CraftedCardEntryFactory(player=self.birds_player, card=self.card, used=CraftedCardEntry.UsedChoice.UNUSED)

        # Give Birds a card (Fox)
        self.hand_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name) # Fox
        HandEntryFactory(player=self.birds_player, card=self.hand_card)

        # Place a Cat warrior in a Fox clearing (Clearing 1)
        self.clearing = Clearing.objects.get(game=self.game, clearing_number=1)
        Warrior.objects.create(player=self.cats_player, clearing=self.clearing)

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

    def test_propaganda_bureau_flow(self):
        """Test Propaganda Bureau flow."""
        self.birds_client.base_route = "/api/action/card/propaganda-bureau/"
        
        # 1. Initial GET -> pick-card
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.birds_client.step = response.data
        self.assertEqual(response.data["name"], "pick-card")
        
        # 2. SUBMIT card -> pick-clearing
        response = self.birds_client.submit_action({"card": CardsEP.AMBUSH_RED.name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-clearing")
        
        # 3. SUBMIT clearing -> pick-opponent
        response = self.birds_client.submit_action({"clearing_number": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-opponent")
        
        # 4. SUBMIT opponent -> completed
        response = self.birds_client.submit_action({"faction": Faction.CATS.value})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify Cat warrior removed, Bird warrior added
        self.assertEqual(Warrior.objects.filter(player=self.cats_player, clearing=self.clearing).count(), 0)
        self.assertEqual(Warrior.objects.filter(player=self.birds_player, clearing=self.clearing).count(), 1)
        # Verify card spent
        self.assertFalse(HandEntry.objects.filter(player=self.birds_player, card=self.hand_card).exists())
