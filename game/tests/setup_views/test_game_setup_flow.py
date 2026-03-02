from django.test import TransactionTestCase
from django.contrib.auth.models import User
from game.models.game_models import Game, Player, Faction, Clearing
from game.models.events.setup import GameSimpleSetup
from game.models.cats.setup import CatsSimpleSetup
from game.models.birds.setup import BirdsSimpleSetup
from game.models.crows.setup import CrowsSimpleSetup
from game.tests.client import RootGameClient
from rest_framework import status

class GameSetupFlowTest(TransactionTestCase):
    """
    Integration test for the full game setup flow with 4 factions.
    Covers creation, joining, picking factions, starting, and setup for:
    Cats, Birds, WA, and Crows.
    """

    def setUp(self):
        # Create 4 users
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        self.user3 = User.objects.create_user(username="user3", password="password")
        self.user4 = User.objects.create_user(username="user4", password="password")

    def test_full_setup_flow(self):
        # 1. User 1 Creates Game
        client1 = RootGameClient("user1", "password", 0) # game_id 0 for now
        response = client1.post("/api/game/create/", data={
            "map_label": Game.BoardMaps.AUTUMN,
            "faction_options": [
                {"faction": Faction.CATS.value},
                {"faction": Faction.BIRDS.value},
                {"faction": Faction.WOODLAND_ALLIANCE.value},
                {"faction": Faction.CROWS.value},
            ]
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        game_id = response.data["game_id"]
        client1.game_id = game_id

        # 2. Users Join Game
        for u, p in [("user1", "password"), ("user2", "password"), ("user3", "password"), ("user4", "password")]:
            c = RootGameClient(u, p, game_id)
            # User 1 is owner but hasn't joined as player yet (create_game doesn't add player)
            res = c.patch(f"/api/game/join/{game_id}/")
            self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        # 3. Users Pick Factions
        factions = [Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE, Faction.CROWS]
        clients = []
        for i, (u, p) in enumerate([("user1", "password"), ("user2", "password"), ("user3", "password"), ("user4", "password")]):
            c = RootGameClient(u, p, game_id)
            res = c.patch(f"/api/game/pick-faction/{game_id}/", data={"faction": factions[i].value})
            self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
            clients.append(c)

        # 4. User 1 Starts Game
        res = client1.patch(f"/api/game/start/{game_id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        # 5. Cats Setup (Player 1)
        cats_client = clients[0]
        cats_client.get_action()
        self.assertEqual(cats_client.base_route, "/api/cats/setup/pick-corner/")
        
        # Pick Corner (Clearing 1)
        res = cats_client.submit_action({"clearing_number": 1})
        self.assertEqual(res.status_code, 200)

        # Place 3 Buildings
        for b_type, cl_num in [("RECRUITER", 1), ("SAWMILL", 5), ("WORKSHOP", 9)]:
            cats_client.get_action()
            # Step 1: Select clearing
            cats_client.submit_action({"clearing_number": cl_num})
            # Step 2: Select building type
            cats_client.submit_action({"building_type": b_type})

        # Confirm
        cats_client.get_action()
        self.assertEqual(cats_client.base_route, "/api/cats/setup/confirm-completed-setup/")
        res = cats_client.submit_action({"confirm": True})
        self.assertEqual(res.status_code, 200)

        # 6. Birds Setup (Player 2)
        birds_client = clients[1]
        birds_client.get_action()
        self.assertEqual(birds_client.base_route, "/api/birds/setup/pick-corner/")
        
        # Pick Corner (Clearing 3 - opposite of Cats at 1)
        res = birds_client.submit_action({"clearing_number": 3})
        self.assertEqual(res.status_code, 200)

        # Choose Leader (Charismatic)
        birds_client.get_action()
        self.assertEqual(birds_client.base_route, "/api/birds/setup/choose-leader/")
        res = birds_client.submit_action({"leader": "CHARISMATIC"})
        self.assertEqual(res.status_code, 200)

        # Confirm
        birds_client.get_action()
        self.assertEqual(birds_client.base_route, "/api/birds/setup/confirm-completed-setup/")
        res = birds_client.submit_action({"confirm": True})
        self.assertEqual(res.status_code, 200)

        # 7. WA Setup - now automatic and bypassed
        # After Birds confirm, it should automatically bypass WA and provide Crows pick clearing
        crows_client = clients[3]
        crows_client.get_action()
        self.assertEqual(crows_client.base_route, "/api/crows/setup/pick-clearing/")

        # 8. Crows Setup (Player 4)
        crows_client = clients[3]
        crows_client.get_action()
        self.assertEqual(crows_client.base_route, "/api/crows/setup/pick-clearing/")
        
        # Place 3 warriors (Fox, Rabbit, Mouse)
        # Clearing 6 (Fox), Clearing 10 (Rabbit), Clearing 2 (Mouse)
        for cl_num in [6, 10, 2]:
            res = crows_client.submit_action({"clearing_number": cl_num})
            self.assertEqual(res.status_code, 200)

        # Confirm
        crows_client.get_action()
        self.assertEqual(crows_client.base_route, "/api/crows/setup/confirm-completed-setup/")
        res = crows_client.submit_action({"confirm": True})
        self.assertEqual(res.status_code, 200)

        # 9. Final Verification
        game = Game.objects.get(pk=game_id)
        self.assertEqual(game.status, Game.GameStatus.SETUP_COMPLETED)
        
        # Verify first player (Cats) has an active turn action
        cats_client.get_action()
        # Should be in Daylight (Crafting) because Birdsong wood placement is automatic
        self.assertEqual(cats_client.base_route, "/api/cats/daylight/craft/")
        
        # Verify wood was automatically placed in clearing 5 (where we placed the sawmill)
        from game.models.cats.tokens import CatWood
        self.assertTrue(CatWood.objects.filter(player__game=game, clearing__clearing_number=5).exists())
