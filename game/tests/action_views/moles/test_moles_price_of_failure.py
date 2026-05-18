from rest_framework import status
from rest_framework.test import APITestCase

from game.models.game_models import Faction
from game.models.events.event import Event, EventType
from game.models.events.moles import PriceOfFailureEvent
from game.models.moles.turn import MoleTurn, MoleBirdsong, MoleDaylight, MoleEvening
from game.models.moles.ministers import Minister
from game.tests.client import RootGameClient
from game.tests.my_factories import MolesBirdsGameSetupFactory, CardFactory


class MolesPriceOfFailureViewBaseTestCase(APITestCase):
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
        self.birdsong = self.turn.birdsong.first()
        self.daylight = self.turn.daylight.first()
        self.evening = self.turn.evening.first()

        # Clear any cards from setup
        from game.models.game_models import HandEntry
        HandEntry.objects.filter(player=self.moles_player).delete()

    def sway_minister(self, name):
        """Sway a minister."""
        minister = Minister.objects.get(player=self.moles_player, name=name)
        minister.swayed = True
        minister.save()
        return minister

    def create_price_of_failure_event(self):
        """Create an active price of failure event."""
        event = Event.objects.create(
            game=self.game, type=EventType.PRICE_OF_FAILURE, is_resolved=False
        )
        PriceOfFailureEvent.objects.create(event=event)
        return event


class MolesPriceOfFailureViewTests(MolesPriceOfFailureViewBaseTestCase):
    def test_get_with_event_shows_available_ministers(self):
        """Test that GET with active event shows available swayed ministers."""
        self.create_price_of_failure_event()

        # Sway one lord
        self.sway_minister(Minister.MinisterName.DUCHESS_OF_MUD)

        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_minister")
        self.assertIn("options", response.data)

        # Should have Duchess option (must select one, no Done option)
        self.assertEqual(len(response.data["options"]), 1)
        self.assertEqual(response.data["options"][0]["value"], Minister.MinisterName.DUCHESS_OF_MUD.value)

    def test_get_with_multiple_lords_shows_all_lords(self):
        """Test that when multiple lords are swayed, all are shown."""
        self.create_price_of_failure_event()

        # Sway all three lords
        self.sway_minister(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway_minister(Minister.MinisterName.EARL_OF_STONE)
        self.sway_minister(Minister.MinisterName.BARON_OF_DIRT)

        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have 3 lords (no Done option since selection is mandatory)
        self.assertEqual(len(response.data["options"]), 3)

    def test_get_ignores_nobles_when_lords_available(self):
        """Test that nobles are not shown when lords are swayed."""
        self.create_price_of_failure_event()

        # Sway one lord and two nobles
        self.sway_minister(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway_minister(Minister.MinisterName.BRIGADIER)
        self.sway_minister(Minister.MinisterName.MAYOR)

        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have only the lord (no nobles or squires)
        self.assertEqual(len(response.data["options"]), 1)
        self.assertEqual(response.data["options"][0]["value"], Minister.MinisterName.DUCHESS_OF_MUD.value)

    def test_get_shows_nobles_when_no_lords_swayed(self):
        """Test that nobles are shown when no lords are swayed."""
        self.create_price_of_failure_event()

        # Sway only nobles
        self.sway_minister(Minister.MinisterName.BRIGADIER)
        self.sway_minister(Minister.MinisterName.MAYOR)

        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have 2 nobles (no lords available)
        self.assertEqual(len(response.data["options"]), 2)

    def test_get_shows_squires_when_no_nobles_or_lords(self):
        """Test that squires are shown when no nobles or lords are swayed."""
        self.create_price_of_failure_event()

        # Sway only squires
        self.sway_minister(Minister.MinisterName.MARSHAL)
        self.sway_minister(Minister.MinisterName.CAPTAIN)

        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have 2 squires (no nobles or lords)
        self.assertEqual(len(response.data["options"]), 2)

    def test_post_with_empty_action_raises_error(self):
        """Test that POST with empty minister raises error."""
        self.create_price_of_failure_event()
        self.sway_minister(Minister.MinisterName.DUCHESS_OF_MUD)

        self.moles_client.get_action()
        response = self.moles_client.submit_action(
            {"minister_name": ""}
        )
        # Empty action should raise validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_with_invalid_minister_raises_error(self):
        """Test that POST with invalid minister name raises error."""
        self.create_price_of_failure_event()

        self.moles_client.get_action()
        response = self.moles_client.submit_action(
            {"minister_name": "INVALID_MINISTER"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid minister", str(response.data))

    def test_post_with_unswayed_minister_raises_error(self):
        """Test that selecting an unswayed minister raises error."""
        self.create_price_of_failure_event()
        self.sway_minister(Minister.MinisterName.DUCHESS_OF_MUD)

        self.moles_client.get_action()
        response = self.moles_client.submit_action(
            {"minister_name": Minister.MinisterName.EARL_OF_STONE.value}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_with_non_highest_rank_raises_error(self):
        """Test that selecting a noble when lords are available raises error."""
        self.create_price_of_failure_event()

        # Sway one lord and one noble
        self.sway_minister(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway_minister(Minister.MinisterName.BRIGADIER)

        self.moles_client.get_action()
        response = self.moles_client.submit_action(
            {"minister_name": Minister.MinisterName.BRIGADIER.value}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_successfully_resolves_price_of_failure(self):
        """Test that selecting a valid minister successfully resolves the event."""
        event = self.create_price_of_failure_event()
        self.sway_minister(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway_minister(Minister.MinisterName.EARL_OF_STONE)

        self.moles_client.get_action()
        response = self.moles_client.submit_action(
            {"minister_name": Minister.MinisterName.DUCHESS_OF_MUD.value}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

        # Verify event is resolved
        event.refresh_from_db()
        self.assertTrue(event.is_resolved)

        # Verify minister is unswayed
        duchess = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.DUCHESS_OF_MUD
        )
        self.assertFalse(duchess.swayed)

        # Verify other lord remains swayed
        earl = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.EARL_OF_STONE
        )
        self.assertTrue(earl.swayed)

    def test_post_with_single_lord_completes(self):
        """Test that selecting the only swayed lord completes the action."""
        event = self.create_price_of_failure_event()
        self.sway_minister(Minister.MinisterName.DUCHESS_OF_MUD)

        self.moles_client.get_action()
        response = self.moles_client.submit_action(
            {"minister_name": Minister.MinisterName.DUCHESS_OF_MUD.value}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_post_with_highest_noble_when_no_lords(self):
        """Test that selecting a noble works when no lords are swayed."""
        event = self.create_price_of_failure_event()
        self.sway_minister(Minister.MinisterName.BRIGADIER)
        self.sway_minister(Minister.MinisterName.MAYOR)

        self.moles_client.get_action()
        response = self.moles_client.submit_action(
            {"minister_name": Minister.MinisterName.BRIGADIER.value}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_post_discards_card_from_hand(self):
        """Test that resolving price of failure discards a card."""
        from game.models.game_models import HandEntry
        from game.game_data.cards.exiles_and_partisans import CardsEP

        event = self.create_price_of_failure_event()
        self.sway_minister(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway_minister(Minister.MinisterName.EARL_OF_STONE)

        # Add a card to hand
        card = CardFactory(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
        HandEntry.objects.create(player=self.moles_player, card=card)

        hand_before = HandEntry.objects.filter(player=self.moles_player).count()

        self.moles_client.get_action()
        response = self.moles_client.submit_action(
            {"minister_name": Minister.MinisterName.DUCHESS_OF_MUD.value}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify a card was discarded
        hand_after = HandEntry.objects.filter(player=self.moles_player).count()
        self.assertEqual(hand_after, hand_before - 1)
