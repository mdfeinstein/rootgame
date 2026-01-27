from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, Game
from game.tests.my_factories import GameSetupWithFactionsFactory
from game.transactions.general import next_step

class WATurnFlowTestCase(TestCase):
    def setUp(self):
        # Create a game with Cats, Birds, and WA
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE])
        
        # Identify players
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.wa_player = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)
        
        # Set up password first so login works
        self.wa_player.user.set_password("password")
        self.wa_player.user.save()
        
        # Set up client for WA player
        self.wa_client = RootGameClient(self.wa_player.user.username, "password", self.game.id)
        
        # Login again because the first one might have failed if password wasn't set
        self.wa_client.login()
        
        # Advance game to WA's turn
        self.game.current_turn = 2
        self.game.save()
        
        # Initialize WA's turn
        next_step(self.wa_player)

    def test_wa_turn_flow(self):
        """
        Test moving through a WA turn by ending all action steps.
        """
        # 1. Birdsong - Revolt Step
        self.wa_client.get_action()
        # Initial action should be WA_REVOLT
        self.assertEqual(self.wa_client.base_route, "/api/wa/birdsong/revolt/")
        # End revolt step. Depending on supporters, it might be 'clearing_number' or 'confirm'
        if "clearing_number" in [d["type"] for d in self.wa_client.step["payload_details"]]:
            self.wa_client.submit_action({"clearing_number": ""})
        else:
            self.wa_client.submit_action({"confirm": True})
        
        # 2. Birdsong - Spread Sympathy Step
        # After completing revolt, it should move to WA_SPREAD_SYMPATHY
        self.assertEqual(self.wa_client.base_route, "/api/wa/birdsong/spread-sympathy/")
        # End spread sympathy step
        if "clearing_number" in [d["type"] for d in self.wa_client.step["payload_details"]]:
            self.wa_client.submit_action({"clearing_number": ""})
        else:
            self.wa_client.submit_action({"confirm": True})
        
        # 3. Daylight - Actions Step
        # After completing spread sympathy, it should move to WA_DAYLIGHT_ACTIONS
        self.assertEqual(self.wa_client.base_route, "/api/wa/daylight/actions/")
        # End daylight actions
        self.wa_client.submit_action({"action_type": ""})
        
        # 4. Evening - Military Operations Step
        # After completing daylight actions, it should move to WA_EVENING (Military Operations)
        self.assertEqual(self.wa_client.base_route, "/api/wa/evening/operations/")
        # End operations
        if "action_type" in [d["type"] for d in self.wa_client.step["payload_details"]]:
            self.wa_client.submit_action({"action_type": ""})
        else:
            self.wa_client.submit_action({"confirm": True})
        
        # 5. Evening - Drawing and Discarding
        # end_evening_operations calls next_step which moves to DRAWING.
        # step_effect for DRAWING calls draw_cards and then next_step (if no informants).
        # draw_cards calls next_step.
        # So it might skip DISCARDING if hand size <= 5.
        
        # Verify that turn has advanced back to the first player (Cats, turn order 0)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, 0)
