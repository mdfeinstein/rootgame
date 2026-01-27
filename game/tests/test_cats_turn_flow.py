from game.models import HandEntry
from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, Game
from game.tests.my_factories import GameSetupWithFactionsFactory
from game.transactions.general import next_step

class CatTurnFlowTestCase(TestCase):
    def setUp(self):
        # Create a game with Cats, Birds, and WA
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE])
        
        # Identify players
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Set up client for Cats player
        self.cats_player.user.set_password("password")
        self.cats_player.user.save()
        self.cats_client = RootGameClient(self.cats_player.user.username, "password", self.game.id)
        
        # Advance game to Cats' turn (turn 0)
        self.game.current_turn = 0
        self.game.save()
        
        # Initialize Cats' turn which should trigger Birdsong auto-placement
        # In actual game, this might have been called by next_players_turn from previous player
        # But for the test, we ensure it's in the starting state.
        # CatBirdsong default is NOT_STARTED. We need to move it to at least verify the auto-flow.
        next_step(self.cats_player)

    def test_cats_turn_flow(self):
        """
        Test moving through a Cats turn by ending all action steps.
        Wood should auto-place, move straight to Daylight.
        """
        # 1. Birdsong check
        self.cats_client.get_action()
        # Since wood should auto-place, it should land on Daylight Crafting
        # (Birdsong NOT_STARTED -> PLACING_WOOD -> check_auto_place_wood -> next_step -> COMPLETED)
        # So current action should be 'cats-daylight-craft'
        self.assertEqual(self.cats_client.base_route, "/api/cats/daylight/craft/")
        
        # 2. Daylight - Crafting Step
        # End crafting step
        self.cats_client.submit_action({"card": ""})
        
        # 3. Daylight - Actions Step
        # It should move to 'cats-daylight-actions'
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.base_route, "/api/cats/daylight/actions/")
        # End action step
        self.cats_client.submit_action({"action_type": ""})
        
        # 4. Evening:
        # draw, discard, and end turn should happen automatically.
        # check for four cards in hand
        cards_in_hand = HandEntry.objects.filter(player=self.cats_player)
        self.assertEqual(cards_in_hand.count(), 4)
        # Verify turn advanced to Birds (turn order 1)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, 1)
        
        birds_player = self.game.players.get(turn_order=1)
        self.assertEqual(birds_player.faction, Faction.BIRDS)
