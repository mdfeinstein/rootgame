from django.test import TestCase
from game.tests.client import RootGameClient
from game.models.game_models import Faction, CraftedCardEntry

from game.tests.my_factories import (
    MolesBirdsGameSetupFactory,
)
from game.models.moles.turn import MoleTurn, MoleBirdsong, MoleDaylight, MoleEvening
from game.game_data.cards.exiles_and_partisans import CardsEP


class MolesTurnFlowTestCase(TestCase):
    def setUp(self):
        # Create a game with Moles and Birds
        self.game = MolesBirdsGameSetupFactory()

        # Identify players
        self.moles_player = self.game.players.get(faction=Faction.MOLES)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)

        # Set up client for Moles player
        self.moles_player.user.set_password("password")
        self.moles_player.user.save()
        self.moles_client = RootGameClient(
            self.moles_player.user.username, "password", self.game.id
        )

        # Advance game to Moles' turn
        self.game.current_turn = self.moles_player.turn_order
        self.game.save()

        # Initialize Moles' turn if it doesn't exist
        if not MoleTurn.objects.filter(player=self.moles_player).exists():
            MoleTurn.create_turn(self.moles_player)
            from game.transactions.moles import step_effect

            step_effect(self.moles_player)

    def test_moles_turn_structure(self):
        """Verify Moles turn has all expected phases."""
        turn = MoleTurn.objects.get(player=self.moles_player)

        # Verify all phases exist
        birdsong = MoleBirdsong.objects.get(turn=turn)
        daylight = MoleDaylight.objects.get(turn=turn)
        evening = MoleEvening.objects.get(turn=turn)

        self.assertIsNotNone(birdsong)
        self.assertIsNotNone(daylight)
        self.assertIsNotNone(evening)

    def test_moles_daylight_actions_available(self):
        """Test that Daylight Actions is available (Birdsong auto-skips)."""
        self.moles_client.get_action()
        # Birdsong PLACE_WARRIORS returns None, so we skip to Daylight
        self.assertEqual(self.moles_client.base_route, "/api/moles/daylight/actions/")

    def test_moles_saboteurs_flow(self):
        """Test that Saboteurs triggers at start of Birdsong and can be skipped."""
        from game.tests.my_factories import CraftedCardEntryFactory, CardFactory
        from game.transactions.moles import step_effect

        # Give Moles the Saboteurs card
        saboteurs_card = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name, suit="w")
        CraftedCardEntryFactory(player=self.moles_player, card=saboteurs_card)

        # Reset turn to test from start
        MoleTurn.objects.filter(player=self.moles_player).delete()
        MoleTurn.create_turn(self.moles_player)

        # Call step_effect to trigger NOT_STARTED handler which calls saboteurs_check
        step_effect(self.moles_player)

        # Now get_action should return saboteurs
        self.moles_client.get_action()
        self.assertEqual(self.moles_client.base_route, "/api/action/card/saboteurs/")

        # Skip saboteurs
        self.moles_client.submit_action({"faction": "skip"})

        # After skip, should move to Daylight Actions (Birdsong auto-skips)
        self.moles_client.get_action()
        self.assertEqual(self.moles_client.base_route, "/api/moles/daylight/actions/")

    def test_moles_eyrie_emigre_flow(self):
        """Test that Eyrie Emigre triggers during Birdsong BEFORE_END step."""
        from game.tests.my_factories import CraftedCardEntryFactory, CardFactory
        from game.transactions.moles import step_effect

        # Give Moles the Eyrie Emigre card (must be UNUSED)
        emigre_card = CardFactory(game=self.game, card_type=CardsEP.EYRIE_EMIGRE.name, suit="w")
        CraftedCardEntryFactory(
            player=self.moles_player,
            card=emigre_card,
            used=CraftedCardEntry.UsedChoice.UNUSED,
        )

        # Set turn to Birdsong BEFORE_END step
        turn = MoleTurn.objects.get(player=self.moles_player)
        birdsong = MoleBirdsong.objects.get(turn=turn)
        birdsong.step = MoleBirdsong.MoleBirdsongSteps.BEFORE_END
        birdsong.save()

        # Call step_effect to trigger is_emigre check
        step_effect(self.moles_player)

        # Get action should return emigre event route
        self.moles_client.get_action()
        self.assertEqual(self.moles_client.base_route, "/api/action/card/eyrie-emigre/")

    def test_moles_charm_offensive_flow(self):
        """Test Charm Offensive is triggered when transitioning to Evening."""
        from game.tests.my_factories import CraftedCardEntryFactory, CardFactory
        from game.transactions.moles import step_effect

        # Give Moles the Charm Offensive card
        charm_card = CardFactory(game=self.game, card_type=CardsEP.CHARM_OFFENSIVE.name, suit="y")
        CraftedCardEntryFactory(player=self.moles_player, card=charm_card)

        # Set up: complete Birdsong and Daylight
        turn = MoleTurn.objects.get(player=self.moles_player)
        birdsong = MoleBirdsong.objects.get(turn=turn)
        birdsong.step = MoleBirdsong.MoleBirdsongSteps.COMPLETED
        birdsong.save()

        daylight = MoleDaylight.objects.get(turn=turn)
        daylight.step = MoleDaylight.MoleDaylightSteps.COMPLETED
        daylight.save()

        evening = MoleEvening.objects.get(turn=turn)
        evening.step = MoleEvening.MoleEveningSteps.NOT_STARTED
        evening.save()

        # Call step_effect to trigger charm_offensive check
        step_effect(self.moles_player)

        # Get action should return charm offensive event route
        self.moles_client.get_action()
        self.assertEqual(self.moles_client.base_route, "/api/action/card/charm-offensive/")

        # Skip charm offensive
        self.moles_client.submit_action({"select": "skip"})

        # Verify we moved past it
        self.assertIsNotNone(self.moles_client.step)
