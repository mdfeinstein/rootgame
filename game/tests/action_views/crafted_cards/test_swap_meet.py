from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, HandEntry, CraftedCardEntry, Warrior, Clearing
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.events.crafted_cards import SwapMeetEvent

class SwapMeetViewTestCase(TestCase):
    def setUp(self):
        # Create game with Cats and Birds
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Setup passwords for client login
        self.birds_player.user.set_password("password")
        self.birds_player.user.save()
        self.cats_player.user.set_password("password")
        self.cats_player.user.save()
        
        self.birds_client = RootGameClient(self.birds_player.user.username, "password", self.game.id)
        
        # Give Birds Swap Meet card
        self.swap_meet_card = CardFactory(game=self.game, card_type=CardsEP.SWAP_MEET.name)
        self.swap_meet_entry = CraftedCardEntryFactory(player=self.birds_player, card=self.swap_meet_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Clear hands for determinism
        HandEntry.objects.filter(player=self.birds_player).delete()
        HandEntry.objects.filter(player=self.cats_player).delete()
        
        # Give Cats a card to take
        self.card_to_take = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name)
        HandEntry.objects.create(player=self.cats_player, card=self.card_to_take)
        
        # Give Birds a card to give back
        self.card_to_give = CardFactory(game=self.game, card_type=CardsEP.FALSE_ORDERS.name)
        HandEntry.objects.create(player=self.birds_player, card=self.card_to_give)

        # Set Birds turn and phase to Birdsong
        from game.models.birds.turn import BirdTurn, BirdBirdsong
        self.game.current_turn = 1
        self.game.save()
        if not BirdTurn.objects.filter(player=self.birds_player).exists():
            BirdTurn.create_turn(self.birds_player)
        
        turn = BirdTurn.objects.filter(player=self.birds_player).order_by("-turn_number").first()
        # Advance to a valid step so get_current_action doesn't crash
        birdsong = BirdBirdsong.objects.get(turn=turn)
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE
        birdsong.save()

    def test_swap_meet_full_flow(self):
        """Test full Swap Meet flow consolidated in one view."""
        # Manually set the base route for the client
        self.birds_client.base_route = "/api/action/card/swap-meet/"
        
        # 1. Initial GET - should be "pick-opponent"
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.birds_client.step = response.data
        self.assertEqual(self.birds_client.step["name"], "pick-opponent")
        
        # Check options: Cats should be there
        options = self.birds_client.step["options"]
        self.assertTrue(any(opt["value"] == Faction.CATS.value for opt in options))

        # 2. SUBMIT "pick-opponent"
        # payload_details: [{"type": "select", "name": "opponent_faction"}]
        response = self.birds_client.submit_action({"select": Faction.CATS.value})
        self.assertEqual(response.status_code, 200)
        
        # Should now be on the next step: "pick-card-to-give"
        self.assertEqual(self.birds_client.step["name"], "pick-card-to-give")
        
        # Verify card was taken
        self.assertTrue(HandEntry.objects.filter(player=self.birds_player, card=self.card_to_take).exists())
        self.assertFalse(HandEntry.objects.filter(player=self.cats_player, card=self.card_to_take).exists())
        
        # Verify event was created
        event = SwapMeetEvent.objects.filter(taking_player=self.birds_player, event__is_resolved=False).first()
        self.assertIsNotNone(event)

        # 3. GET "pick-card-to-give" (re-verifying branching logic in GET)
        # This is implicitly done by submit_action if it doesn't return "completed", 
        # but my submit_action logic in RootGameClient calls get_action if "completed"
        # Since pick-opponent POST returns the next step, self.birds_client.step is already updated.
        
        # 4. SUBMIT "pick-card-to-give"
        # payload_details: [{"type": "card", "name": "card_name"}]
        response = self.birds_client.submit_action({"card": self.card_to_give.card_type})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify card was given back
        self.assertTrue(HandEntry.objects.filter(player=self.cats_player, card=self.card_to_give).exists())
        self.assertFalse(HandEntry.objects.filter(player=self.birds_player, card=self.card_to_give).exists())
        
        # Verify event was resolved
        event.event.refresh_from_db()
        self.assertTrue(event.event.is_resolved)
        
        # Verify Swap Meet card marked as used
        self.swap_meet_entry.refresh_from_db()
        self.assertEqual(self.swap_meet_entry.used, CraftedCardEntry.UsedChoice.USED)
