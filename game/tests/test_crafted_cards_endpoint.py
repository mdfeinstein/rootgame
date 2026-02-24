from game.models import BirdDaylight
from django.test import TestCase, Client
from django.contrib.auth.models import User
from game.models.game_models import (
    Game,
    Player,
    Faction,
    Card,
    CraftedCardEntry,
    DeckEntry,
)
from game.models.birds.turn import BirdTurn, BirdBirdsong, BirdDaylight, BirdEvening
from game.game_data.cards.exiles_and_partisans import CardsEP


class TestCraftedCardsEndpoint(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="test_user")
        self.game = Game.objects.create(pk=1, owner=self.user)
        self.player = Player.objects.create(
            game=self.game, user=self.user, faction=Faction.BIRDS, turn_order=0
        )
        self.client = Client()

        # Create a BirdBirdsong phase
        self.bird_turn = BirdTurn.objects.create(player=self.player, turn_number=1)
        self.birdson = BirdBirdsong.objects.create(
            turn=self.bird_turn, step="1"  # Start of birdsong for Saboteurs test
        )
        self.daylight = BirdDaylight.objects.create(turn=self.bird_turn, step="0")
        self.evening = BirdEvening.objects.create(turn=self.bird_turn, step="0")

        # Create needed cards
        self.saboteurs_card = Card.objects.create(
            game=self.game, suit="Bird", card_type=CardsEP.SABOTEURS.name
        )
        self.informants_card = Card.objects.create(
            game=self.game, suit="Fox", card_type=CardsEP.INFORMANTS.name
        )

        # Craft Saboteurs (Should be useful in Birdsong start)
        self.crafted_saboteurs = CraftedCardEntry.objects.create(
            player=self.player,
            card=self.saboteurs_card,
            used=CraftedCardEntry.UsedChoice.UNUSED,
        )

        # Craft Informants (Should NOT be useful in Birdsong)
        self.crafted_informants = CraftedCardEntry.objects.create(
            player=self.player,
            card=self.informants_card,
            used=CraftedCardEntry.UsedChoice.UNUSED,
        )

        # Craft Used Card (Should NOT be useful)
        self.crafted_used = CraftedCardEntry.objects.create(
            player=self.player,
            card=self.saboteurs_card,
            used=CraftedCardEntry.UsedChoice.USED,
        )

    def test_get_crafted_cards(self):
        response = self.client.get(
            f"/api/crafted-cards/{self.game.pk}/{Faction.BIRDS}/"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data), 3)

        # Sort by card name or some identifier to be deterministic if needed,
        # or just find by property
        saboteurs = next(
            item
            for item in data
            if item["card"]["card_name"] == "SABOTEURS" and item["used"] is False
        )
        informants = next(
            item for item in data if item["card"]["card_name"] == "INFORMANTS"
        )
        used = next(item for item in data if item["used"] is True)

        # Saboteurs should be active in Birdsong
        self.assertTrue(saboteurs["has_active"])
        self.assertFalse(saboteurs["used"])
        self.assertIsNotNone(saboteurs["action_endpoint"])
        self.assertIn("saboteurs", saboteurs["action_endpoint"])

        # Informants should NOT be active in Birdsong
        self.assertTrue(informants["has_active"])
        self.assertFalse(informants["used"])
        self.assertIsNone(informants["action_endpoint"])

        # Used card should be marked used and no endpoint
        self.assertTrue(used["used"])
        self.assertIsNone(used["action_endpoint"])
