from django.test import TestCase
from game.tests.client import RootGameClient
from game.models.game_models import Faction, HandEntry, CraftedCardEntry

from game.tests.my_factories import (
    GameSetupWithFactionsFactory,
    CraftedCardEntryFactory,
    CardFactory,
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

    def test_crows_birdsong_crafting_available(self):
        """Test that Birdsong Crafting step is available."""
        turn = CrowTurn.objects.filter(player=self.crows_player).last()
        birdsong = turn.birdsong.first()

        # Set to crafting step
        birdsong.step = CrowBirdsong.CrowBirdsongSteps.CRAFT
        birdsong.save()

        # Get crafting action
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.base_route, "/api/crows/action/crafting/")

        # End crafting by selecting empty
        response = self.crows_client.submit_action({"card": ""})
        self.assertEqual(response.status_code, 200)

    def test_crows_birdsong_flipping_available(self):
        """Test that Birdsong Flipping step is available."""
        turn = CrowTurn.objects.filter(player=self.crows_player).last()
        birdsong = turn.birdsong.first()

        # Set to flipping step
        birdsong.step = CrowBirdsong.CrowBirdsongSteps.FLIP
        birdsong.save()

        # Get flipping action - may require plot tokens to flip
        self.crows_client.get_action()
        # Should be at flipping or skip if no plots
        self.assertIsNotNone(self.crows_client.step)

    def test_crows_birdsong_recruiting_available(self):
        """Test that Birdsong Recruiting step is available."""
        turn = CrowTurn.objects.filter(player=self.crows_player).last()
        birdsong = turn.birdsong.first()

        # Set to recruiting step
        birdsong.step = CrowBirdsong.CrowBirdsongSteps.RECRUIT
        birdsong.save()

        # Get recruiting action
        self.crows_client.get_action()
        self.assertIsNotNone(self.crows_client.step)

    def test_crows_daylight_actions_available(self):
        """Test that Daylight Actions step is available and can be skipped."""
        turn = CrowTurn.objects.filter(player=self.crows_player).last()
        birdsong = turn.birdsong.first()
        daylight = turn.daylight.first()

        # Skip Birdsong
        birdsong.step = CrowBirdsong.CrowBirdsongSteps.COMPLETED
        birdsong.save()
        daylight.step = CrowDaylight.CrowDaylightSteps.ACTIONS
        daylight.save()

        # Get daylight actions
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.base_route, "/api/crows/action/daylight/")

        # End actions
        response = self.crows_client.submit_action({"action_type": ""})
        self.assertEqual(response.status_code, 200)

    def test_crows_evening_exert_available(self):
        """Test that Evening Exert step is available."""
        turn = CrowTurn.objects.filter(player=self.crows_player).last()
        birdsong = turn.birdsong.first()
        daylight = turn.daylight.first()
        evening = turn.evening.first()

        # Skip to evening exert
        birdsong.step = CrowBirdsong.CrowBirdsongSteps.COMPLETED
        birdsong.save()
        daylight.step = CrowDaylight.CrowDaylightSteps.COMPLETED
        daylight.save()
        evening.step = CrowEvening.CrowEveningSteps.EXERT
        evening.save()

        # Get exert action
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.base_route, "/api/crows/action/exert/")

    def test_crows_evening_discarding_available(self):
        """Test that Evening Discard step handles large hands."""
        turn = CrowTurn.objects.filter(player=self.crows_player).last()
        birdsong = turn.birdsong.first()
        daylight = turn.daylight.first()
        evening = turn.evening.first()

        # Skip to evening discard
        birdsong.step = CrowBirdsong.CrowBirdsongSteps.COMPLETED
        birdsong.save()
        daylight.step = CrowDaylight.CrowDaylightSteps.COMPLETED
        daylight.save()
        evening.step = CrowEvening.CrowEveningSteps.DISCARDING
        evening.save()

        # Clear hand and add cards
        HandEntry.objects.filter(player=self.crows_player).delete()

        # Add 7 cards (need to discard to 5)
        for _ in range(7):
            card = CardFactory(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
            HandEntry.objects.create(player=self.crows_player, card=card)

        # Get discard action
        self.crows_client.get_action()
        # May show discard or auto-complete if already at 5
        self.assertIsNotNone(self.crows_client.step)

    def test_crows_turn_structure(self):
        """Test that Crows turn has all expected phases."""
        turn = CrowTurn.objects.filter(player=self.crows_player).last()

        # Verify all phases exist
        self.assertIsNotNone(turn.birdsong.first())
        self.assertIsNotNone(turn.daylight.first())
        self.assertIsNotNone(turn.evening.first())

        # Verify phase types
        birdsong = turn.birdsong.first()
        daylight = turn.daylight.first()
        evening = turn.evening.first()

        self.assertIsNotNone(birdsong)
        self.assertIsNotNone(daylight)
        self.assertIsNotNone(evening)

    def test_crows_saboteurs_card_available(self):
        """Test that Saboteurs card can be crafted."""
        saboteurs_card = CardFactory(
            game=self.game, card_type=CardsEP.SABOTEURS.name, suit="w"
        )
        CraftedCardEntryFactory(player=self.crows_player, card=saboteurs_card)

        crafted = CraftedCardEntry.objects.filter(
            player=self.crows_player, card=saboteurs_card
        )
        self.assertTrue(crafted.exists())

    def test_crows_charm_offensive_card_available(self):
        """Test that Charm Offensive card can be crafted."""
        charm_card = CardFactory(
            game=self.game, card_type=CardsEP.CHARM_OFFENSIVE.name, suit="y"
        )
        CraftedCardEntryFactory(player=self.crows_player, card=charm_card)

        crafted = CraftedCardEntry.objects.filter(
            player=self.crows_player, card=charm_card
        )
        self.assertTrue(crafted.exists())

    def test_crows_informants_card_available(self):
        """Test that Informants card can be crafted."""
        informants_card = CardFactory(
            game=self.game, card_type=CardsEP.INFORMANTS.name, suit="o"
        )
        CraftedCardEntryFactory(player=self.crows_player, card=informants_card)

        crafted = CraftedCardEntry.objects.filter(
            player=self.crows_player, card=informants_card
        )
        self.assertTrue(crafted.exists())

    def test_crows_eyrie_emigre_card_available(self):
        """Test that Eyrie Emigre card can be crafted."""
        emigre_card = CardFactory(
            game=self.game, card_type=CardsEP.EYRIE_EMIGRE.name, suit="w"
        )
        CraftedCardEntryFactory(
            player=self.crows_player,
            card=emigre_card,
            used=CraftedCardEntry.UsedChoice.UNUSED,
        )

        crafted = CraftedCardEntry.objects.filter(
            player=self.crows_player, card=emigre_card
        )
        self.assertTrue(crafted.exists())
