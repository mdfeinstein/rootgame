from rest_framework import status
from rest_framework.test import APITestCase
from game.models.game_models import Faction, Clearing
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowTurn
from game.serializers.game_state_serializer import GameStateSerializer
from game.tests.client import RootGameClient
from game.tests.my_factories import GameSetupFactory

class CrowsGamestateTests(APITestCase):
    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.CATS, Faction.CROWS])
        self.crows_player = self.game.players.get(faction=Faction.CROWS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Cats user
        self.cats_user = self.cats_player.user
        self.cats_user.set_password("p")
        self.cats_user.save()
        self.cats_client = RootGameClient(user=self.cats_user, password="p", game_id=self.game.id)
        
        # Crows user
        self.crows_user = self.crows_player.user
        self.crows_user.set_password("p")
        self.crows_user.save()
        self.crows_client = RootGameClient(user=self.crows_user, password="p", game_id=self.game.id)
        
        # Clearings
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        
        CrowTurn.create_turn(self.crows_player)
        self.game.current_turn = self.crows_player.turn_order
        self.game.save()
        
        # Setup tokens: 1 in reserve, 1 faceup on board, 1 facedown on board
        self.reserve_token = PlotToken.objects.filter(player=self.crows_player, plot_type=PlotToken.PlotType.BOMB).first()
        # Reserve token is naturally in reserve and facedown.
        
        self.faceup_token = PlotToken.objects.filter(player=self.crows_player, plot_type=PlotToken.PlotType.SNARE).first()
        self.faceup_token.clearing = self.c1
        self.faceup_token.is_facedown = False
        self.faceup_token.save()
        
        self.facedown_token = PlotToken.objects.filter(player=self.crows_player, plot_type=PlotToken.PlotType.EXTORTION).first()
        self.facedown_token.clearing = self.c2
        self.facedown_token.is_facedown = True
        self.facedown_token.save()

    def test_public_gamestate_endpoint(self):
        """
        Public endpoint should return masked type for facedown tokens, but explicit type for faceup tokens.
        It should also exclude tokens in reserve.
        """
        response = self.cats_client.get(f"/api/crows/player-info/{self.game.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        tokens = data["tokens"]["plots"]
        
        # We put 2 tokens on the board
        self.assertEqual(len(tokens), 2)
        
        faceup_data = next(t for t in tokens if t["id"] == self.faceup_token.id)
        facedown_data = next(t for t in tokens if t["id"] == self.facedown_token.id)
        
        # Faceup token exposes its type
        self.assertFalse(faceup_data["is_facedown"])
        self.assertEqual(faceup_data["plot_type"], PlotToken.PlotType.SNARE.value)
        self.assertEqual(faceup_data["clearing_number"], self.c1.clearing_number)
        
        # Facedown token hides its type
        self.assertTrue(facedown_data["is_facedown"])
        self.assertIsNone(facedown_data["plot_type"])
        self.assertEqual(facedown_data["clearing_number"], self.c2.clearing_number)
        
        # Reserve token count exposed but object not returned
        self.assertEqual(data["reserve_plots_count"], 6) # Starts with 8, 2 moved to board

        try:
            serializer = GameStateSerializer(self.game)
            data = serializer.data
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e
        
        # find crows player payload from players array
        crows_payload = next(p for p in data["players"] if p["id"] == self.crows_player.id)
        
        tokens = crows_payload["faction_state"]["tokens"]["plots"]
        self.assertEqual(len(tokens), 2)
        facedown_data = next(t for t in tokens if t["id"] == self.facedown_token.id)
        self.assertIsNone(facedown_data["plot_type"])

    def test_private_gamestate_endpoint(self):
        """
        Private endpoint must be restricted to Crows player, and return fully unmasked
        facedown tokens alongside reserve tokens.
        """
        # Cats player gets 401
        response = self.cats_client.get(f"/api/crows/player-private-info/{self.game.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        try:
            response = self.crows_client.get(f"/api/crows/player-private-info/{self.game.id}/")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        
        reserve = data["reserve_plots"]
        facedown = data["facedown_plots"]
        
        # Reserve tokens (6 total) all have explicit types available
        self.assertEqual(len(reserve), 6)
        reserve_data = next(t for t in reserve if t["id"] == self.reserve_token.id)
        self.assertEqual(reserve_data["plot_type"], PlotToken.PlotType.BOMB.value)
        self.assertIsNone(reserve_data["clearing_number"])
        
        # Facedown board tokens (1 total) have their type unmasked to the Crows
        self.assertEqual(len(facedown), 1)
        facedown_data = facedown[0]
        self.assertEqual(facedown_data["id"], self.facedown_token.id)
        self.assertEqual(facedown_data["plot_type"], PlotToken.PlotType.EXTORTION.value)
        self.assertEqual(facedown_data["clearing_number"], self.c2.clearing_number)
