from django.test import TestCase

from game.errors import UnavailableActionError, IllegalActionError
from game.models.game_models import Faction, Clearing, Warrior
from game.models.moles.buildings import Citadel, Market
from game.models.moles.tokens import Tunnel
from game.models.moles.crown import Crown
from game.models.moles.ministers import Minister
from game.models.moles.burrow import Burrow
from game.models.moles.setup import MolesSimpleSetup
from game.models.events.setup import GameSimpleSetup
from game.tests.my_factories import GameSetupFactory
from game.transactions.moles_setup import (
    start_simple_moles_setup,
    pick_corner,
    confirm_completed_setup,
)


class MolesSetupBaseTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.MOLES, Faction.CATS])
        self.player = self.game.players.get(faction=Faction.MOLES)
        self.cats_player = self.game.players.get(faction=Faction.CATS)

        self.game_setup = GameSimpleSetup.objects.get(game=self.game)
        self.game_setup.status = GameSimpleSetup.GameSetupStatus.MOLES_SETUP
        self.game_setup.save()

        try:
            self.moles_setup = MolesSimpleSetup.objects.get(player=self.player)
        except MolesSimpleSetup.DoesNotExist:
            self.moles_setup = start_simple_moles_setup(self.player)


class MolesInitialSetupTests(MolesSetupBaseTestCase):
    def test_initial_object_counts(self):
        self.assertEqual(Warrior.objects.filter(player=self.player).count(), 20)
        self.assertEqual(
            Warrior.objects.filter(player=self.player, clearing__isnull=True).count(),
            20,
        )
        self.assertEqual(Tunnel.objects.filter(player=self.player).count(), 3)
        self.assertEqual(
            Tunnel.objects.filter(player=self.player, clearing__isnull=True).count(), 3
        )
        self.assertEqual(Citadel.objects.filter(player=self.player).count(), 3)
        self.assertEqual(Market.objects.filter(player=self.player).count(), 3)
        self.assertEqual(Minister.objects.filter(player=self.player).count(), 9)
        self.assertEqual(Crown.objects.filter(player=self.player).count(), 9)
        self.assertEqual(
            Crown.objects.filter(
                player=self.player, type=Crown.CrownType.SQUIRE
            ).count(),
            3,
        )
        self.assertEqual(
            Crown.objects.filter(
                player=self.player, type=Crown.CrownType.NOBLE
            ).count(),
            3,
        )
        self.assertEqual(
            Crown.objects.filter(player=self.player, type=Crown.CrownType.LORD).count(),
            3,
        )
        self.assertEqual(Burrow.objects.filter(player=self.player).count(), 1)

    def test_all_ministers_created_unswayed(self):
        self.assertEqual(
            Minister.objects.filter(player=self.player, swayed=False).count(), 9
        )
        expected_names = {
            Minister.MinisterName.MARSHAL,
            Minister.MinisterName.CAPTAIN,
            Minister.MinisterName.FOREMOLE,
            Minister.MinisterName.BRIGADIER,
            Minister.MinisterName.MAYOR,
            Minister.MinisterName.BANKER,
            Minister.MinisterName.DUCHESS_OF_MUD,
            Minister.MinisterName.EARL_OF_STONE,
            Minister.MinisterName.BARON_OF_DIRT,
        }
        actual_names = set(
            Minister.objects.filter(player=self.player).values_list("name", flat=True)
        )
        self.assertEqual(actual_names, expected_names)


class MolesPickCornerTests(MolesSetupBaseTestCase):
    def test_pick_corner_places_pieces(self):
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        pick_corner(self.player, c1)

        self.assertEqual(
            Warrior.objects.filter(player=self.player, clearing=c1).count(), 2
        )
        self.assertEqual(
            Tunnel.objects.filter(player=self.player, clearing=c1).count(), 1
        )
        self.assertEqual(
            Tunnel.objects.filter(player=self.player, clearing__isnull=True).count(), 2
        )

        for adj in c1.connected_clearings.all():
            self.assertEqual(
                Warrior.objects.filter(player=self.player, clearing=adj).count(),
                2,
                f"Expected 2 warriors in clearing {adj.clearing_number}",
            )

        self.moles_setup.refresh_from_db()
        self.assertEqual(
            self.moles_setup.step, MolesSimpleSetup.Steps.PENDING_CONFIRMATION
        )

    def test_pick_corner_non_corner_raises(self):
        c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        with self.assertRaises(IllegalActionError):
            pick_corner(self.player, c5)

    def test_pick_corner_wrong_step_raises(self):
        self.moles_setup.step = MolesSimpleSetup.Steps.PENDING_CONFIRMATION
        self.moles_setup.save()
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        with self.assertRaises(UnavailableActionError):
            pick_corner(self.player, c1)

    def test_pick_corner_wrong_game_status_raises(self):
        self.game_setup.status = GameSimpleSetup.GameSetupStatus.CATS_SETUP
        self.game_setup.save()
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        with self.assertRaises(UnavailableActionError):
            pick_corner(self.player, c1)


class MolesConfirmSetupTests(MolesSetupBaseTestCase):
    def setUp(self):
        super().setUp()
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        pick_corner(self.player, c1)
        self.moles_setup.refresh_from_db()

    def test_confirm_advances_game_setup(self):
        confirm_completed_setup(self.player)
        self.moles_setup.refresh_from_db()
        self.assertEqual(self.moles_setup.step, MolesSimpleSetup.Steps.COMPLETED)
        self.game_setup.refresh_from_db()
        self.assertNotEqual(
            self.game_setup.status, GameSimpleSetup.GameSetupStatus.MOLES_SETUP
        )

    def test_confirm_wrong_step_raises(self):
        self.moles_setup.step = MolesSimpleSetup.Steps.PICKING_CORNER
        self.moles_setup.save()
        with self.assertRaises(UnavailableActionError):
            confirm_completed_setup(self.player)
