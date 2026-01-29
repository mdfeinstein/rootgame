from typing import cast
from django.test import Client, TestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from django.core.management import call_command

from game.models.game_models import Faction, Game, Player
from game.serializers.bird_serializers import BirdSerializer
from game.serializers.cat_serializers import CatSerializer
from game.tests.client import RootGameClient


def login_client(client: APIClient, user: str):
    response = client.post(
        "/api/token/", data={"username": user, "password": "password"}
    )
    print(response.json())
    token = response.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class CreateGameTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        self.user3 = User.objects.create_user(username="user3", password="password")

    def test_create_game_not_logged_in(self):
        response = create_game(self.client, {"map_label": "Autumn"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_game_wrong_map(self):
        self.client.force_login(user=self.user1)
        response = create_game(self.client, {"map_label": "wrong_map"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_game_valid(self):
        self.client.force_login(user=self.user1)
        response = create_game(self.client, {"map_label": "Autumn"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


def create_game(client: Client, data):
    return client.post("/api/game/create/", data=data)


class JoinGameTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        self.user3 = User.objects.create_user(username="user3", password="password")
        self.user4 = User.objects.create_user(username="user4", password="password")
        self.client.force_login(user=self.user1)
        response = create_game(self.client, {"map_label": "Autumn"})
        self.game_id = response.data["game_id"]
        self.client.logout()

    def test_not_logged_in(self):
        response = join_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_single_joined_ok(self):
        self.client.force_login(user=self.user2)
        response = join_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_three_joined_ok_fourth_rejected(self):
        # this will fail when more factions are added as default will be larger list of faction entries
        self.client.force_login(user=self.user1)
        response = join_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.client.force_login(user=self.user2)
        response = join_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.client.force_login(user=self.user3)
        response = join_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.client.force_login(user=self.user4)
        response = join_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_join_twice(self):
        self.client.force_login(user=self.user2)
        response = join_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = join_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


def join_game(client: Client, game_id: int):
    return client.patch(f"/api/game/join/{game_id}/")


class PickFactionTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        self.user3 = User.objects.create_user(username="user3", password="password")
        self.client.force_login(user=self.user1)
        # create game
        response = create_game(self.client, {"map_label": "Autumn"})
        self.game_id = response.data["game_id"]
        # all players join
        join_game(self.client, self.game_id)
        self.client.force_login(user=self.user2)
        join_game(self.client, self.game_id)
        self.client.force_login(user=self.user3)
        join_game(self.client, self.game_id)
        self.client.logout()

    def test_not_logged_in(self):
        response = pick_faction(self.client, self.game_id, "Cats")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_players_pick_unique_factions(self):
        self.client.force_login(user=self.user1)
        response = pick_faction(self.client, self.game_id, "Cats")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.client.force_login(user=self.user2)
        response = pick_faction(self.client, self.game_id, "Birds")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.client.force_login(user=self.user3)
        response = pick_faction(self.client, self.game_id, "Woodland Alliance")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_players_pick_same_faction(self):
        self.client.force_login(user=self.user1)
        response = pick_faction(self.client, self.game_id, "Cats")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.client.force_login(user=self.user2)
        response = pick_faction(self.client, self.game_id, "Cats")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.client.force_login(user=self.user3)
        response = pick_faction(self.client, self.game_id, "Cats")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_players_pick_faction_not_in_list(self):
        self.client.force_login(user=self.user1)
        response = pick_faction(self.client, self.game_id, "helloworld")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


def pick_faction(client: Client, game_id: int, faction: str):
    return client.patch(
        f"/api/game/pick-faction/{game_id}/",
        data={"faction": faction},
    )


class StartGameTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        self.user3 = User.objects.create_user(username="user3", password="password")
        self.client.force_login(user=self.user1)
        # create game
        response = create_game(self.client, data={"map_label": "Autumn"})
        self.game_id = response.data["game_id"]
        # all players join and pick faction
        join_game(self.client, self.game_id)
        pick_faction(self.client, self.game_id, "Cats")
        self.client.force_login(user=self.user2)
        join_game(self.client, self.game_id)
        pick_faction(self.client, self.game_id, "Birds")
        self.client.force_login(user=self.user3)
        join_game(self.client, self.game_id)
        pick_faction(self.client, self.game_id, "Woodland Alliance")
        self.client.logout()

    def test_not_logged_in(self):
        response = start_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_start_game_as_owner(self):
        self.client.force_login(user=self.user1)
        response = start_game(self.client, self.game_id)
        print("game started")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_start_game_as_non_owner(self):
        self.client.force_login(user=self.user2)
        response = start_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_start_game_twice(self):
        # will fail. need to add a game status field so we can check if its started and block a second start
        self.client.force_login(user=self.user1)
        response = start_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = start_game(self.client, self.game_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # def start_game(self):
    #     return self.client.patch(f"/api/game/start/{self.game_id}/")


def start_game(client: Client, game_id: int):
    return client.patch(f"/api/game/start/{game_id}/")


class CatsSetupTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        self.user3 = User.objects.create_user(username="user3", password="password")
        # self.client.force_login(user=self.user1)
        login_client(self.client, self.user1.username)
        response = create_game(self.client, data={"map_label": "Autumn"})
        print(response.data)
        self.game_id = response.data["game_id"]
        join_game(self.client, self.game_id)
        pick_faction(self.client, self.game_id, "Cats")
        # self.client.force_login(user=self.user2)
        login_client(self.client, self.user2.username)
        join_game(self.client, self.game_id)
        pick_faction(self.client, self.game_id, "Birds")
        # self.client.force_login(user=self.user3)
        login_client(self.client, self.user3.username)
        join_game(self.client, self.game_id)
        pick_faction(self.client, self.game_id, "Woodland Alliance")
        self.client.logout()
        # self.client.force_login(user=self.user1)
        login_client(self.client, self.user1.username)
        start_game(self.client, self.game_id)

    def test_components_created(self):
        # check that cat components are created
        cats_player = Player.objects.get(game=self.game_id, faction=Faction.CATS)
        # request cats data
        response = self.client.get(f"/api/cats/player-info/{self.game_id}/")
        print("response data: ", response.json())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # check component counts
        self.assertEqual(len(response.data["warriors"]), 25)
        self.assertEqual(len(response.data["tokens"]["wood"]), 8)
        self.assertIsNone(response.data["tokens"]["keep"]["clearing_number"])
        self.assertEqual(len(response.data["buildings"]["workshops"]), 6)
        self.assertEqual(len(response.data["buildings"]["recruiters"]), 6)
        self.assertEqual(len(response.data["buildings"]["sawmills"]), 6)
        self.assertEqual(response.data["player"]["card_count"], 3)

    def test_picked_not_corner(self):
        self.client.force_login(user=self.user1)
        response = cats_pick_corner(self.client, self.game_id, 6)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_player_picked_corner(self):
        self.client.force_login(user=self.user2)
        response = cats_pick_corner(self.client, self.game_id, 1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_placing_building_too_early(self):
        self.client.force_login(user=self.user1)
        response = cats_place_initial_building(
            self.client, self.game_id, 1, "Recruiter"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_picked_corner(self):
        self.client.force_login(user=self.user1)
        response = cats_pick_corner(self.client, self.game_id, 1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cats_full_setup(self):
        """test the "happy path" of a fully valid cats setup"""
        cat_client = RootGameClient(self.user1.username, "password", self.game_id)
        # login_client(self.client, self.user1.username)
        cat_client.login()
        # call_command(
        #     "dumpdata",
        #     "game",
        #     "auth.user",
        #     "--natural-foreign",
        #     "--indent=2",
        #     "--exclude=contenttypes",
        #     "--exclude=auth.permission",
        #     "--exclude=admin",
        #     "--exclude=sessions",
        #     output="game/fixtures/cats_begin_setup.json",
        # )
        # client looks up current action and step
        response = cat_client.get_action()
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # submit clearing number for corner
        response = cat_client.submit_action({"clearing_number": 1})
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # submit confirmation
        response = cat_client.submit_action({"confirm": True})
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # place initial buildings
        self.place_initial_building(cat_client, 10, "Recruiter")
        self.place_initial_building(cat_client, 5, "Workshop")
        self.place_initial_building(cat_client, 1, "Sawmill")
        # placements complete. confirm
        response = cat_client.submit_action({"confirm": True})
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        call_command(
            "dumpdata",
            "game",
            "auth.user",
            "--natural-foreign",
            "--indent=2",
            "--exclude=contenttypes",
            "--exclude=auth.permission",
            "--exclude=admin",
            "--exclude=sessions",
            output="game/fixtures/cats_done_setup.json",
        )
        #check that score is 0
        score = Player.objects.get(game=self.game_id, faction=Faction.CATS).score
        self.assertEqual(score, 0)
        # response = cats_confirm_completed_setup(self.client, self.game_id)
        # self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # check some things

    def place_initial_building(
        self, cat_client, clearing_number: int, building_type: str
    ):
        # submit clearing number for building
        response = cat_client.submit_action({"clearing_number": clearing_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        print(data)
        # submit building type
        response = cat_client.submit_action({"building_type": building_type})
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # submit confirm
        response = cat_client.submit_action({"confirm": True})
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BirdsSetupTestCase(TestCase):
    fixtures = ["cats_done_setup.json"]

    def setUp(self):
        self.game_id = 1
        # self.client = RootGameClient("user2", "password", self.game_id)

    def test_birds_full_setup(self):
        """test the "happy path" of a fully valid birds setup"""
        # birds setup
        client = RootGameClient("user2", "password", self.game_id)
        response = client.get_action()
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # submit clearing number for corner
        response = client.submit_action({"clearing_number": 3})
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # submit confirmation
        response = client.submit_action({"confirm": True})
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # select leader
        response = client.submit_action({"leader": "Despot"})
        print(response.json())
        # confirm leader
        response = client.submit_action({"confirm": True})
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # final setup confirmation
        response = client.submit_action({"confirm": True})
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # check stuff...
        response = get_bird_player_public(self.client, self.game_id)
        print(response.json())

        call_command(
            "dumpdata",
            "game",
            "auth.user",
            "--natural-foreign",
            "--indent=2",
            "--exclude=contenttypes",
            "--exclude=auth.permission",
            "--exclude=admin",
            "--exclude=sessions",
            output="game/fixtures/birds_finished_setup.json",
        )


def get_bird_player_public(client: Client, game_id: int):
    return client.get(f"/api/birds/player-info/{game_id}/")
