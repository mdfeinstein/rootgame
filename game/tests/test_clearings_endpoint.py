from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from game.tests.my_factories import GameSetupWithFactionsFactory, UserFactory
from game.models.game_models import Faction


class ClearingEndpointTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.game = GameSetupWithFactionsFactory(
            owner=self.user, factions=[Faction.CATS, Faction.BIRDS]
        )

    def test_get_clearings_endpoint(self):
        url = f"/api/clearings/{self.game.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that ruins are present in some clearings (at least 6, 10, 11, 12 in autumn setup)
        data = response.json()
        self.assertEqual(len(data), 12)
        has_ruins = any(len(c["ruins"]) > 0 for c in data)
        self.assertTrue(has_ruins)
