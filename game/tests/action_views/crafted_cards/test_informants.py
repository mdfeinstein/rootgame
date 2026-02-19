from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, CraftedCardEntry, Card, DiscardPileEntry
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory, DiscardPileEntryFactory
from game.game_data.cards.exiles_and_partisans import CardsEP

class InformantsViewTestCase(TestCase):
    def setUp(self):
        # Create game with Cats and Birds
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        
        # Setup passwords for client login
        self.birds_player.user.set_password("password")
        self.birds_player.user.save()
        
        self.birds_client = RootGameClient(self.birds_player.user.username, "password", self.game.id)
        
        # Give Birds Informants card
        self.card = CardFactory(game=self.game, card_type=CardsEP.INFORMANTS.name)
        self.entry = CraftedCardEntryFactory(player=self.birds_player, card=self.card, used=CraftedCardEntry.UsedChoice.UNUSED)

        # Place an ambush card in discard pile
        self.ambush_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        DiscardPileEntryFactory(game=self.game, card=self.ambush_card)

        # Set Birds turn and phase to Evening (Drawing step)
        from game.models.birds.turn import BirdTurn, BirdEvening
        self.game.current_turn = 1
        self.game.save()
        if not BirdTurn.objects.filter(player=self.birds_player).exists():
            BirdTurn.create_turn(self.birds_player)
            
        turn = BirdTurn.objects.filter(player=self.birds_player).order_by("-turn_number").first()
        
        # Complete birdsong and daylight
        from game.models.birds.turn import BirdBirdsong, BirdDaylight
        birdsong = BirdBirdsong.objects.get(turn=turn)
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()
        
        daylight = BirdDaylight.objects.get(turn=turn)
        daylight.step = BirdDaylight.BirdDaylightSteps.COMPLETED
        daylight.save()

        evening = BirdEvening.objects.get(turn=turn)
        evening.step = BirdEvening.BirdEveningSteps.DRAWING
        evening.save()

        # Create Informants Event
        from game.models.events.crafted_cards import InformantsEvent
        self.event_entry = InformantsEvent.create(self.entry)

    def test_informants_flow(self):
        """Test Informants flow."""
        self.birds_client.base_route = "/api/action/card/informants/"
        
        # 1. Initial GET -> use-or-skip
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.birds_client.step = response.data
        self.assertEqual(response.data["name"], "use-or-skip")
        
        # 2. SUBMIT "use" -> pick-ambush-card
        response = self.birds_client.submit_action({"choice": "use"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-ambush-card")
        
        # 3. SUBMIT ambush -> completed
        response = self.birds_client.submit_action({"card": CardsEP.AMBUSH_RED.name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify ambush card is in hand
        from game.models.game_models import HandEntry
        self.assertTrue(HandEntry.objects.filter(player=self.birds_player, card__card_type=CardsEP.AMBUSH_RED.name).exists())
        # Verify discard pile is empty (of this card)
        self.assertFalse(DiscardPileEntry.objects.filter(game=self.game, card__card_type=CardsEP.AMBUSH_RED.name).exists())

    def test_informants_skip(self):
        """Test skipping Informants."""
        self.birds_client.base_route = "/api/action/card/informants/"
        
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.birds_client.step = response.data
        response = self.birds_client.submit_action({"choice": "skip"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify card marked as used
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.used, CraftedCardEntry.UsedChoice.USED)
