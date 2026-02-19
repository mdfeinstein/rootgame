from django.test import TestCase
from django.contrib.auth.models import User
from game.models.game_models import Game, Player, FactionChoiceEntry, Faction
from rest_framework.test import APIClient
from rest_framework import status


class GameListingTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")

        # Game 1: Owned by user1, user1 is a player
        self.game1 = Game.objects.create(
            owner=self.user1, status=Game.GameStatus.NOT_STARTED
        )
        Player.objects.create(game=self.game1, user=self.user1)
        # Add faction choices so players can join
        for faction in Faction:
            FactionChoiceEntry.objects.create(game=self.game1, faction=faction)

        # Game 2: Owned by user2, user2 is a player
        self.game2 = Game.objects.create(
            owner=self.user2, status=Game.GameStatus.NOT_STARTED
        )
        Player.objects.create(game=self.game2, user=self.user2)
        for faction in Faction:
            FactionChoiceEntry.objects.create(game=self.game2, faction=faction)

    def test_list_active_games(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/games/active/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.game1.id)

    def test_list_joinable_games(self):
        self.client.force_authenticate(user=self.user1)
        # game2 should be joinable for user1
        response = self.client.get("/api/games/joinable/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.game2.id)

    def test_join_game(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.patch(f"/api/game/join/{self.game2.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Now game2 should be in active games
        response = self.client.get("/api/games/active/")
        self.assertEqual(len(response.data), 2)

        # And game2 should no longer be in joinable games
        response = self.client.get("/api/games/joinable/")
        self.assertEqual(len(response.data), 0)
