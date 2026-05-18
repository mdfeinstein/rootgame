from rest_framework import status
from rest_framework.test import APITestCase
from django.db import models

from game.models.game_models import Faction, Clearing, HandEntry, Card
from game.models.moles.turn import MoleTurn, MoleDaylight, MoleEvening
from game.models.moles.buildings import Citadel, Market
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.tests.client import RootGameClient
from game.tests.my_factories import MolesBirdsGameSetupFactory, CardFactory


class MolesEveningViewBaseTestCase(APITestCase):
    def setUp(self):
        self.game = MolesBirdsGameSetupFactory()
        self.moles_player = self.game.players.get(faction=Faction.MOLES)

        # Moles user
        self.moles_user = self.moles_player.user
        self.moles_user.set_password("p")
        self.moles_user.save()
        self.moles_client = RootGameClient(
            user=self.moles_user, password="p", game_id=self.game.id
        )

        # Set turn to Moles
        self.game.current_turn = self.moles_player.turn_order
        self.game.save()

        # Get or create a turn for Moles
        self.turn = MoleTurn.objects.filter(player=self.moles_player).last()
        if not self.turn:
            self.turn = MoleTurn.create_turn(self.moles_player)

        # Get phases
        from game.models.moles.turn import MoleBirdsong, MoleDaylight
        self.birdsong = self.turn.birdsong.first()
        self.daylight = self.turn.daylight.first()
        self.evening = self.turn.evening.first()

        # Complete birdsong and daylight phases to get to evening
        if self.birdsong:
            self.birdsong.step = MoleBirdsong.MoleBirdsongSteps.COMPLETED
            self.birdsong.save()
        if self.daylight:
            self.daylight.step = MoleDaylight.MoleDaylightSteps.COMPLETED
            self.daylight.save()

        # Clear any cards from setup
        HandEntry.objects.filter(player=self.moles_player).delete()

    def add_card_to_hand(self, card_enum):
        """Add a card to player hand."""
        card = CardFactory(game=self.game, card_type=card_enum.name)
        HandEntry.objects.create(player=self.moles_player, card=card)

    def get_building_by_clearing(self, clearing_num, building_type="citadel"):
        """Get or create a building in a clearing."""
        clearing = Clearing.objects.get(game=self.game, clearing_number=clearing_num)
        if building_type == "citadel":
            building = Citadel.objects.filter(player=self.moles_player, building_slot__clearing=clearing).first()
            if not building:
                from game.models.game_models import BuildingSlot
                # Get the next available building_slot_number for this clearing
                max_slot = BuildingSlot.objects.filter(clearing=clearing).aggregate(models.Max('building_slot_number'))['building_slot_number__max'] or 0
                slot = BuildingSlot.objects.create(clearing=clearing, building_slot_number=max_slot + 1)
                building = Citadel.objects.create(player=self.moles_player, building_slot=slot)
        else:
            building = Market.objects.filter(player=self.moles_player, building_slot__clearing=clearing).first()
            if not building:
                from game.models.game_models import BuildingSlot
                # Get the next available building_slot_number for this clearing
                max_slot = BuildingSlot.objects.filter(clearing=clearing).aggregate(models.Max('building_slot_number'))['building_slot_number__max'] or 0
                slot = BuildingSlot.objects.create(clearing=clearing, building_slot_number=max_slot + 1)
                building = Market.objects.create(player=self.moles_player, building_slot=slot)
        return building


class MolesCraftingViewTests(MolesEveningViewBaseTestCase):
    def setUp(self):
        super().setUp()
        self.evening.step = MoleEvening.MoleEveningSteps.CRAFT
        self.evening.save()

    def test_crafting_get_shows_cards_in_hand(self):
        """Test that GET shows available cards in hand."""
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)
        self.add_card_to_hand(CardsEP.CROSSBOW_WILD)

        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_card")
        self.assertIn("options", response.data)
        # Should have at least 2 cards + Done option
        self.assertGreaterEqual(len(response.data["options"]), 3)

    def test_crafting_done_completes_step(self):
        """Test that selecting Done completes the crafting step."""
        self.moles_client.get_action()
        response = self.moles_client.submit_action({"card": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_crafting_select_card_shows_clearing_options(self):
        """Test that selecting a card shows clearing options."""
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)
        building1 = self.get_building_by_clearing(1, "citadel")
        building2 = self.get_building_by_clearing(2, "citadel")

        self.moles_client.get_action()
        response = self.moles_client.submit_action(
            {"card": CardsEP.RABBIT_PARTISANS.name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_clearing")
        self.assertEqual(response.data["endpoint"], "clearing")
        self.assertIn("options", response.data)

    def test_crafting_invalid_card_raises(self):
        """Test that selecting an invalid card raises error."""
        self.moles_client.get_action()
        response = self.moles_client.submit_action(
            {"card": "INVALID_CARD"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MolesDiscardViewTests(MolesEveningViewBaseTestCase):
    def setUp(self):
        super().setUp()
        self.evening.step = MoleEvening.MoleEveningSteps.DISCARD
        self.evening.save()

    def test_discard_with_hand_5_or_less_completes(self):
        """Test that with 5 or fewer cards, discard is auto-completed."""
        # Add exactly 5 cards
        for _ in range(5):
            self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_discard_with_hand_over_5_shows_cards(self):
        """Test that with more than 5 cards, discard shows card options."""
        # Add 7 cards
        for _ in range(7):
            self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_card")
        self.assertEqual(response.data["endpoint"], "card")
        self.assertIn("options", response.data)
        # Should have 7 card options
        self.assertEqual(len(response.data["options"]), 7)

    def test_discard_one_card_reduces_hand(self):
        """Test that discarding one card reduces hand size."""
        # Add 6 cards
        for _ in range(6):
            self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        self.moles_client.get_action()

        # Get the first card's HandEntry ID from the options
        response_data = self.moles_client.get_action()
        card_id = response_data.data["options"][0]["value"]

        response = self.moles_client.submit_action(
            {"card": card_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should still be on select_card since hand is 5 but we need to go to exactly 5
        # After discarding 1 from 6, we have 5, so should be completed
        self.assertEqual(response.data["name"], "completed")

    def test_discard_multiple_cards_until_done(self):
        """Test discarding multiple cards until hand reaches 5."""
        # Add 8 cards
        for _ in range(8):
            self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        self.moles_client.get_action()

        # Discard first card
        response_data = self.moles_client.get_action()
        card_id_1 = response_data.data["options"][0]["value"]
        response = self.moles_client.submit_action({"card": card_id_1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be back to select_card (7 cards left, need to discard 2 more)
        self.assertEqual(response.data["name"], "select_card")

        # Discard second card
        card_id_2 = response.data["options"][0]["value"]
        response = self.moles_client.submit_action({"card": card_id_2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should now be completed (6 cards left, need 1 more)
        # Wait, 8 - 2 = 6, need to discard 1 more to get to 5
        self.assertEqual(response.data["name"], "select_card")

        # Discard third card to reach exactly 5
        card_id_3 = response.data["options"][0]["value"]
        response = self.moles_client.submit_action({"card": card_id_3})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")
