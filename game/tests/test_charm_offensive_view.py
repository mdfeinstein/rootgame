from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, CraftedCardEntry
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.events.crafted_cards import CharmOffensiveEvent

class CharmOffensiveViewTestCase(TestCase):
    def setUp(self):
        # Create game with Cats and Birds
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Setup passwords for client login
        self.birds_player.user.set_password("password")
        self.birds_player.user.save()
        
        self.birds_client = RootGameClient(self.birds_player.user.username, "password", self.game.id)
        
        # Give Birds Charm Offensive card
        self.charm_card = CardFactory(game=self.game, card_type=CardsEP.CHARM_OFFENSIVE.name)
        self.charm_entry = CraftedCardEntryFactory(player=self.birds_player, card=self.charm_card, used=CraftedCardEntry.UsedChoice.UNUSED)

        # Set Birds turn and phase to Evening (needed for Charm Offensive)
        from game.models.birds.turn import BirdTurn, BirdBirdsong, BirdDaylight, BirdEvening
        self.game.current_turn = 1
        self.game.save()
        if not BirdTurn.objects.filter(player=self.birds_player).exists():
            BirdTurn.create_turn(self.birds_player)
        
        turn = BirdTurn.objects.filter(player=self.birds_player).order_by("-turn_number").first()
        birdsong = BirdBirdsong.objects.get(turn=turn)
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()
        daylight = BirdDaylight.objects.get(turn=turn)
        daylight.step = BirdDaylight.BirdDaylightSteps.COMPLETED
        daylight.save()
        evening = BirdEvening.objects.get(turn=turn)
        evening.step = BirdEvening.BirdEveningSteps.SCORING
        evening.save()

        # Create the event
        CharmOffensiveEvent.create(self.charm_entry)

    def test_charm_offensive_flow(self):
        """Test Charm Offensive flow."""
        self.birds_client.base_route = "/api/action/card/charm-offensive/"
        
        # 1. Initial GET
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.birds_client.step = response.data
        self.assertEqual(response.data["name"], "pick-opponent")
        
        # 2. SUBMIT "pick-opponent"
        from game.models.checkpoint_models import Action
        actions_before = Action.objects.count()
        response = self.birds_client.submit_action({"select": Faction.CATS.value})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify Score
        self.birds_player.refresh_from_db()
        self.cats_player.refresh_from_db()
        self.assertEqual(self.cats_player.score, 1)
        self.assertEqual(self.birds_player.score, 0)
        
        # Verify Action Record
        self.assertGreater(Action.objects.count(), actions_before)

    def test_charm_offensive_skip(self):
        """Test skipping Charm Offensive."""
        self.birds_client.base_route = "/api/action/card/charm-offensive/"
        
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.birds_client.step = response.data
        response = self.birds_client.submit_action({"select": "skip"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        self.assertEqual(self.cats_player.score, 0)
        self.assertEqual(self.birds_player.score, 0)
