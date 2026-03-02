from rest_framework import status
from rest_framework.test import APITestCase
from game.models.game_models import Faction, Clearing, Warrior
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowTurn, CrowBirdsong, CrowDaylight, CrowEvening
from game.tests.client import RootGameClient
from game.tests.my_factories import GameSetupWithFactionsFactory

class CrowsActionViewsTests(APITestCase):
    def setUp(self):
        # Use WithFactions to ensure setup steps are completed
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.CROWS])
        self.crows_player = self.game.players.get(faction=Faction.CROWS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Crows user
        self.crows_user = self.crows_player.user
        self.crows_user.set_password("p")
        self.crows_user.save()
        self.crows_client = RootGameClient(user=self.crows_user, password="p", game_id=self.game.id)
        
        # Clearings (1 and 5 are adjacent in Autumn map)
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        
        # Set turn to Crows
        self.game.current_turn = self.crows_player.turn_order
        self.game.save()
        
        # Enforce turn object existence
        self.turn = CrowTurn.objects.filter(player=self.crows_player).last()
        if not self.turn:
            self.turn = CrowTurn.create_turn(self.crows_player)
        self.birdsong = self.turn.birdsong.first()
        self.daylight = self.turn.daylight.first()
        self.evening = self.turn.evening.first()

    def test_crows_flipping_view(self):
        """Test flipping a facedown plot token in Birdsong"""
        self.birdsong.step = CrowBirdsong.CrowBirdsongSteps.FLIP
        self.birdsong.save()

        # Place a facedown plot token and a Crow warrior
        plot = PlotToken.objects.filter(player=self.crows_player, plot_type=PlotToken.PlotType.BOMB).first()
        plot.clearing = self.c1
        plot.is_facedown = True
        plot.save()
        
        Warrior.objects.create(player=self.crows_player, clearing=self.c1)
        
        # 1. Get current action
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.step["name"], "select_plot_to_flip")
        
        # 2. Submit flip
        response = self.crows_client.submit_action({"clearing_number": self.c1.clearing_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")
        
        plot.refresh_from_db()
        self.assertFalse(plot.is_facedown)

    def test_crows_daylight_plot(self):
        """Test daylight plot action flow"""
        self.birdsong.step = CrowBirdsong.CrowBirdsongSteps.COMPLETED
        self.birdsong.save()
        self.daylight.step = CrowDaylight.CrowDaylightSteps.ACTIONS
        self.daylight.actions_remaining = 3
        self.daylight.plots_placed = 0
        self.daylight.save()
        
        # Need 1 warrior for cost 1
        Warrior.objects.create(player=self.crows_player, clearing=self.c5)
        
        # 1. Get action
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.step["name"], "select_action")
        
        # 2. Select Plot
        response = self.crows_client.submit_action({"action_type": "plot"})
        self.assertEqual(response.data["name"], "plot_clearing")
        
        # 3. Select Clearing
        response = self.crows_client.submit_action({"clearing_number": self.c5.clearing_number})
        self.assertEqual(response.data["name"], "plot_type")
        
        # 4. Select Plot Type
        reserve_token = PlotToken.objects.filter(player=self.crows_player, clearing__isnull=True).first()
        response = self.crows_client.submit_action({"plot_type": reserve_token.plot_type})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")
        
        self.assertTrue(PlotToken.objects.filter(clearing=self.c5, plot_type=reserve_token.plot_type).exists())

    def test_crows_evening_exert(self):
        """Test exerting in Evening"""
        self.birdsong.step = CrowBirdsong.CrowBirdsongSteps.COMPLETED
        self.birdsong.save()
        self.daylight.step = CrowDaylight.CrowDaylightSteps.COMPLETED
        self.daylight.save()
        self.evening.step = CrowEvening.CrowEveningSteps.EXERT
        self.evening.save()
        
        Warrior.objects.create(player=self.crows_player, clearing=self.c1)

        # 1. Get action
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.step["name"], "select_exert_action")
        
        # 2. Select Move (c1 to c5 which is adjacent)
        response = self.crows_client.submit_action({"action_type": "move"})
        self.assertEqual(response.data["name"], "move_origin")
        
        # 3. Origin select
        response = self.crows_client.submit_action({"clearing_number": self.c1.clearing_number})
        self.assertEqual(response.data["name"], "move_destination")
        
        # 4. Destination select
        response = self.crows_client.submit_action({"clearing_number": self.c5.clearing_number})
        self.assertEqual(response.data["name"], "move_count")
        
        # 5. Count select
        response = self.crows_client.submit_action({"number": 1})
        self.assertEqual(response.data["name"], "completed")
        
        self.assertEqual(Warrior.objects.filter(clearing=self.c5, player=self.crows_player).count(), 1)
        self.evening.refresh_from_db()
        self.assertTrue(self.evening.exert_used)
        self.assertEqual(self.evening.step, CrowEvening.CrowEveningSteps.COMPLETED)

    def test_crows_daylight_plot_cost_increases(self):
        """Test that plotting cost increases when plots_placed is 1"""
        self.birdsong.step = CrowBirdsong.CrowBirdsongSteps.COMPLETED
        self.birdsong.save()
        self.daylight.step = CrowDaylight.CrowDaylightSteps.ACTIONS
        self.daylight.actions_remaining = 3
        self.daylight.plots_placed = 1 # Cost is now 2
        self.daylight.save()
        
        # Need 2 warriors for cost 2 (plots_placed=1 + 1)
        # Place only 1 warrior first to verify failure
        Warrior.objects.create(player=self.crows_player, clearing=self.c5)
        
        self.crows_client.get_action()
        self.crows_client.submit_action({"action_type": "plot"})
        self.crows_client.submit_action({"clearing_number": self.c5.clearing_number})
        
        reserve_token = PlotToken.objects.filter(player=self.crows_player, clearing__isnull=True).first()
        response = self.crows_client.submit_action({"plot_type": reserve_token.plot_type})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Not enough warriors", str(response.data))
        
        # Now add the second warrior and it should pass
        Warrior.objects.create(player=self.crows_player, clearing=self.c5)
        
        response = self.crows_client.submit_action({"plot_type": reserve_token.plot_type})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")
        self.assertTrue(PlotToken.objects.filter(clearing=self.c5, plot_type=reserve_token.plot_type).exists())
