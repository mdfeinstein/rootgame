from django.test import TestCase
from game.tests.client import RootGameClient
from game.models.game_models import Faction, CraftedCardEntry

from game.tests.my_factories import (
    GameSetupWithFactionsFactory,
)
from game.models.crows.turn import CrowTurn, CrowBirdsong, CrowDaylight, CrowEvening
from game.game_data.cards.exiles_and_partisans import CardsEP


class CrowsTurnFlowTestCase(TestCase):
    def setUp(self):
        # Create a game with Crows and Cats
        self.game = GameSetupWithFactionsFactory(
            factions=[Faction.CROWS, Faction.CATS]
        )

        # Identify players
        self.crows_player = self.game.players.get(faction=Faction.CROWS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)

        # Set up client for Crows player
        self.crows_player.user.set_password("password")
        self.crows_player.user.save()
        self.crows_client = RootGameClient(
            self.crows_player.user.username, "password", self.game.id
        )

        # Advance game to Crows' turn
        self.game.current_turn = self.crows_player.turn_order
        self.game.save()

        # Initialize Crows' turn if it doesn't exist
        if not CrowTurn.objects.filter(player=self.crows_player).exists():
            CrowTurn.create_turn(self.crows_player)
            from game.transactions.crows import step_effect

            step_effect(self.crows_player)

    def test_crows_turn_structure(self):
        """Verify Crows turn has all expected phases."""
        turn = CrowTurn.objects.get(player=self.crows_player)

        # Verify all phases exist
        birdsong = CrowBirdsong.objects.get(turn=turn)
        daylight = CrowDaylight.objects.get(turn=turn)
        evening = CrowEvening.objects.get(turn=turn)

        self.assertIsNotNone(birdsong)
        self.assertIsNotNone(daylight)
        self.assertIsNotNone(evening)

        # Verify initial steps
        self.assertEqual(birdsong.step, CrowBirdsong.CrowBirdsongSteps.CRAFT)
        self.assertEqual(daylight.step, CrowDaylight.CrowDaylightSteps.NOT_STARTED)
        self.assertEqual(evening.step, CrowEvening.CrowEveningSteps.NOT_STARTED)

    def test_crows_birdsong_route(self):
        """Test that Birdsong crafting is available."""
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.base_route, "/api/crows/action/crafting/")

    def test_crows_saboteurs_flow(self):
        """Test that Saboteurs triggers at start of Birdsong and can be skipped."""
        from game.tests.my_factories import CraftedCardEntryFactory, CardFactory
        from game.transactions.crows import step_effect

        # Give Crows the Saboteurs card
        saboteurs_card = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name, suit="w")
        CraftedCardEntryFactory(player=self.crows_player, card=saboteurs_card)

        # Reset turn to test from start
        CrowTurn.objects.filter(player=self.crows_player).delete()
        CrowTurn.create_turn(self.crows_player)

        # Call step_effect to trigger card checks
        step_effect(self.crows_player)

        # Now get_action should return saboteurs
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.base_route, "/api/action/card/saboteurs/")

        # Skip saboteurs
        self.crows_client.submit_action({"faction": "skip"})

        # After skip, should move to Birdsong Crafting
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.base_route, "/api/crows/action/crafting/")

    def test_crows_eyrie_emigre_flow(self):
        """Test that Eyrie Emigre triggers during Birdsong BEFORE_END step."""
        from game.tests.my_factories import CraftedCardEntryFactory, CardFactory
        from game.transactions.crows import step_effect

        # Give Crows the Eyrie Emigre card (must be UNUSED)
        emigre_card = CardFactory(game=self.game, card_type=CardsEP.EYRIE_EMIGRE.name, suit="w")
        CraftedCardEntryFactory(
            player=self.crows_player,
            card=emigre_card,
            used=CraftedCardEntry.UsedChoice.UNUSED,
        )

        # Set turn to Birdsong BEFORE_END step
        turn = CrowTurn.objects.get(player=self.crows_player)
        birdsong = CrowBirdsong.objects.get(turn=turn)
        birdsong.step = CrowBirdsong.CrowBirdsongSteps.BEFORE_END
        birdsong.save()

        # Call step_effect to trigger is_emigre check
        step_effect(self.crows_player)

        # Get action should return emigre event route
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.base_route, "/api/action/card/eyrie-emigre/")

    def test_crows_charm_offensive_flow(self):
        """Test that Charm Offensive triggers during Daylight BEFORE_END step."""
        from game.tests.my_factories import CraftedCardEntryFactory, CardFactory
        from game.transactions.crows import step_effect

        # Give Crows the Charm Offensive card
        charm_card = CardFactory(game=self.game, card_type=CardsEP.CHARM_OFFENSIVE.name, suit="y")
        CraftedCardEntryFactory(player=self.crows_player, card=charm_card)

        # Set turn to Daylight BEFORE_END step
        turn = CrowTurn.objects.get(player=self.crows_player)
        birdsong = CrowBirdsong.objects.get(turn=turn)
        birdsong.step = CrowBirdsong.CrowBirdsongSteps.COMPLETED
        birdsong.save()

        daylight = CrowDaylight.objects.get(turn=turn)
        daylight.step = CrowDaylight.CrowDaylightSteps.BEFORE_END
        daylight.save()

        # Call step_effect to trigger check_charm_offensive
        step_effect(self.crows_player)

        # Get action should return charm offensive event route
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.base_route, "/api/action/card/charm-offensive/")

    def test_crows_informants_flow(self):
        """Test that Informants triggers during Evening DRAWING step."""
        from game.tests.my_factories import CraftedCardEntryFactory, CardFactory
        from game.transactions.crows import step_effect

        # Give Crows the Informants card
        informants_card = CardFactory(game=self.game, card_type=CardsEP.INFORMANTS.name, suit="o")
        CraftedCardEntryFactory(player=self.crows_player, card=informants_card)

        # Set turn to Evening DRAWING step
        turn = CrowTurn.objects.get(player=self.crows_player)
        birdsong = CrowBirdsong.objects.get(turn=turn)
        birdsong.step = CrowBirdsong.CrowBirdsongSteps.COMPLETED
        birdsong.save()

        daylight = CrowDaylight.objects.get(turn=turn)
        daylight.step = CrowDaylight.CrowDaylightSteps.COMPLETED
        daylight.save()

        evening = CrowEvening.objects.get(turn=turn)
        evening.step = CrowEvening.CrowEveningSteps.DRAWING
        evening.save()

        # Call step_effect to trigger informants check
        step_effect(self.crows_player)

        # Get action should return informants event route
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.base_route, "/api/action/card/informants/")
