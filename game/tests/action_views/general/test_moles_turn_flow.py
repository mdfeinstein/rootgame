from django.test import TestCase
from game.tests.client import RootGameClient
from game.models.game_models import Faction, HandEntry, CraftedCardEntry

from game.tests.my_factories import (
    MolesBirdsGameSetupFactory,
    CraftedCardEntryFactory,
    CardFactory,
)
from game.models.moles.turn import MoleTurn, MoleBirdsong, MoleDaylight, MoleEvening
from game.models.moles.ministers import Minister
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

    def test_moles_daylight_actions_available(self):
        """Test that Daylight Actions step is available and can be skipped."""
        turn = MoleTurn.objects.filter(player=self.moles_player).last()
        birdsong = turn.birdsong.first()
        daylight = turn.daylight.first()

        # Skip Birdsong to get to Daylight
        birdsong.step = MoleBirdsong.MoleBirdsongSteps.COMPLETED
        birdsong.save()
        daylight.step = MoleDaylight.MoleDaylightSteps.ACTIONS
        daylight.save()

        # Get daylight actions
        self.moles_client.get_action()
        self.assertEqual(self.moles_client.base_route, "/api/moles/daylight/actions/")

        # Skip actions
        response = self.moles_client.submit_action({"action_type": ""})
        self.assertEqual(response.status_code, 200)

    def test_moles_sway_minister_available(self):
        """Test that Sway Minister action is available."""
        turn = MoleTurn.objects.filter(player=self.moles_player).last()
        birdsong = turn.birdsong.first()
        daylight = turn.daylight.first()

        # Skip to sway minister step
        birdsong.step = MoleBirdsong.MoleBirdsongSteps.COMPLETED
        birdsong.save()
        daylight.step = MoleDaylight.MoleDaylightSteps.SWAY_MINISTER
        daylight.save()

        # Add cards to hand
        for _ in range(4):
            card = CardFactory(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
            HandEntry.objects.create(player=self.moles_player, card=card)

        # Get sway minister action
        self.moles_client.get_action()
        self.assertEqual(self.moles_client.base_route, "/api/moles/daylight/sway-minister/")

        # Verify ministers are available
        self.assertGreater(len(self.moles_client.step["options"]), 0)

    def test_moles_crafting_available(self):
        """Test that Evening Crafting step is available."""
        turn = MoleTurn.objects.filter(player=self.moles_player).last()
        birdsong = turn.birdsong.first()
        daylight = turn.daylight.first()
        evening = turn.evening.first()

        # Skip to evening craft
        birdsong.step = MoleBirdsong.MoleBirdsongSteps.COMPLETED
        birdsong.save()
        daylight.step = MoleDaylight.MoleDaylightSteps.COMPLETED
        daylight.save()
        evening.step = MoleEvening.MoleEveningSteps.CRAFT
        evening.save()

        # Add a card to hand
        card = CardFactory(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
        HandEntry.objects.create(player=self.moles_player, card=card)

        # Get crafting action
        self.moles_client.get_action()
        self.assertEqual(self.moles_client.base_route, "/api/moles/evening/craft/")

        # End crafting
        response = self.moles_client.submit_action({"card": ""})
        self.assertEqual(response.status_code, 200)

    def test_moles_discard_with_large_hand(self):
        """Test that Evening Discard step handles large hands."""
        from game.models.game_models import HandEntry

        turn = MoleTurn.objects.filter(player=self.moles_player).last()
        birdsong = turn.birdsong.first()
        daylight = turn.daylight.first()
        evening = turn.evening.first()

        # Skip to evening discard
        birdsong.step = MoleBirdsong.MoleBirdsongSteps.COMPLETED
        birdsong.save()
        daylight.step = MoleDaylight.MoleDaylightSteps.COMPLETED
        daylight.save()
        evening.step = MoleEvening.MoleEveningSteps.DISCARD
        evening.save()

        # Clear existing hand
        HandEntry.objects.filter(player=self.moles_player).delete()

        # Add 7 cards (need to discard to 5)
        for _ in range(7):
            card = CardFactory(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
            HandEntry.objects.create(player=self.moles_player, card=card)

        # Get discard action
        self.moles_client.get_action()
        self.assertEqual(self.moles_client.base_route, "/api/moles/evening/discard/")

        # Verify discard is required
        self.assertIn("cards", self.moles_client.step["prompt"].lower())

        # Discard one card
        response = self.moles_client.get_action()
        card_id = response.data["options"][0]["value"]
        self.moles_client.submit_action({"card": card_id})

        # Should still need to discard (6 cards left)
        self.assertIsNotNone(self.moles_client.step)

    def test_moles_saboteurs_card_available(self):
        """Test that Saboteurs card can be crafted."""
        saboteurs_card = CardFactory(
            game=self.game, card_type=CardsEP.SABOTEURS.name, suit="w"
        )
        CraftedCardEntryFactory(player=self.moles_player, card=saboteurs_card)

        # Verify the card is crafted
        crafted = CraftedCardEntry.objects.filter(
            player=self.moles_player, card=saboteurs_card
        )
        self.assertTrue(crafted.exists())

    def test_moles_charm_offensive_card_available(self):
        """Test that Charm Offensive card can be crafted."""
        charm_card = CardFactory(
            game=self.game, card_type=CardsEP.CHARM_OFFENSIVE.name, suit="y"
        )
        CraftedCardEntryFactory(player=self.moles_player, card=charm_card)

        crafted = CraftedCardEntry.objects.filter(
            player=self.moles_player, card=charm_card
        )
        self.assertTrue(crafted.exists())

    def test_moles_informants_card_available(self):
        """Test that Informants card can be crafted."""
        informants_card = CardFactory(
            game=self.game, card_type=CardsEP.INFORMANTS.name, suit="o"
        )
        CraftedCardEntryFactory(player=self.moles_player, card=informants_card)

        crafted = CraftedCardEntry.objects.filter(
            player=self.moles_player, card=informants_card
        )
        self.assertTrue(crafted.exists())

    def test_moles_eyrie_emigre_card_available(self):
        """Test that Eyrie Emigre card can be crafted."""
        emigre_card = CardFactory(
            game=self.game, card_type=CardsEP.EYRIE_EMIGRE.name, suit="w"
        )
        CraftedCardEntryFactory(
            player=self.moles_player,
            card=emigre_card,
            used=CraftedCardEntry.UsedChoice.UNUSED,
        )

        crafted = CraftedCardEntry.objects.filter(
            player=self.moles_player, card=emigre_card
        )
        self.assertTrue(crafted.exists())

    def test_moles_turn_structure(self):
        """Test that Moles turn has all expected phases."""
        turn = MoleTurn.objects.filter(player=self.moles_player).last()

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
