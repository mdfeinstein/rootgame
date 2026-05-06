from django.test import TestCase
from game.tests.client import RootGameClient
from game.models.game_models import Faction
from game.models.moles.setup import MolesSimpleSetup
from game.models.events.setup import GameSimpleSetup
from game.tests.my_factories import GameSetupFactory
from game.transactions.cats_setup import pick_corner as cats_pick_corner, confirm_completed_setup as cats_confirm


class MolesSetupFlowTestCase(TestCase):
    def setUp(self):
        # Create a game with Cats and Moles
        self.game = GameSetupFactory(
            factions=[Faction.CATS, Faction.MOLES],
        )

        # Identify players
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        self.moles_player = self.game.players.get(faction=Faction.MOLES)

        # Set up client for Moles player
        self.moles_player.user.set_password("password")
        self.moles_player.user.save()
        self.moles_client = RootGameClient(
            self.moles_player.user.username, "password", self.game.id
        )

        # Complete Cats setup (so validate_corner has a reference corner)
        cats_pick_corner(self.cats_player, self.game.clearing_set.get(clearing_number=1))
        # Place 3 buildings
        from game.models.cats.buildings import CatBuildingTypes
        for building_type, clearing_num in [(CatBuildingTypes.RECRUITER, 1), (CatBuildingTypes.SAWMILL, 5), (CatBuildingTypes.WORKSHOP, 9)]:
            from game.transactions.cats_setup import place_initial_building
            place_initial_building(self.cats_player, self.game.clearing_set.get(clearing_number=clearing_num), building_type)
        cats_confirm(self.cats_player)

        # Advance to Moles setup
        game_setup = GameSimpleSetup.objects.get(game=self.game)
        game_setup.status = GameSimpleSetup.GameSetupStatus.MOLES_SETUP
        game_setup.save()

    def test_moles_pick_corner_flow(self):
        """Test that Moles can pick a corner and advance setup."""
        # Get initial action
        self.moles_client.get_action()
        self.assertEqual(self.moles_client.base_route, "/api/moles/setup/pick-corner/")

        # Pick corner (clearing 3, opposite from Cat's Keep at 1)
        response = self.moles_client.submit_action({"clearing_number": 3})
        self.assertEqual(response.status_code, 200)

        # Verify step advanced to PENDING_CONFIRMATION
        moles_setup = MolesSimpleSetup.objects.get(player=self.moles_player)
        self.assertEqual(moles_setup.step, MolesSimpleSetup.Steps.PENDING_CONFIRMATION)

    def test_moles_confirm_setup_flow(self):
        """Test that Moles can confirm setup completion."""
        # First pick a corner
        self.moles_client.get_action()
        self.moles_client.submit_action({"clearing_number": 3})

        # Get confirm action
        self.moles_client.get_action()
        self.assertEqual(
            self.moles_client.base_route, "/api/moles/setup/confirm-completed-setup/"
        )

        # Submit confirmation
        response = self.moles_client.submit_action({"confirm": True})
        self.assertEqual(response.status_code, 200)

        # Verify step advanced to COMPLETED
        moles_setup = MolesSimpleSetup.objects.get(player=self.moles_player)
        self.assertEqual(moles_setup.step, MolesSimpleSetup.Steps.COMPLETED)
