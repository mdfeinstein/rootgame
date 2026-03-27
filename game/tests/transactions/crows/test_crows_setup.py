from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, Suit
from game.models.crows.setup import CrowsSimpleSetup
from game.models.crows.tokens import PlotToken
from game.models.events.setup import GameSimpleSetup
from game.models.cats.tokens import CatKeep
from game.tests.my_factories import GameSetupFactory
from game.transactions.crows_setup import place_initial_warrior, confirm_completed_setup, start_simple_crows_setup
from game.transactions.cats_setup import pick_corner, place_initial_building
from game.tests.logging_mixin import LoggingTestMixin
from game.models.game_log import LogType


class CrowSetupBaseTestCase(LoggingTestMixin, TestCase):
    def setUp(self):
        # Create a game with Cats and Crows
        self.game = GameSetupFactory(factions=[Faction.CATS, Faction.CROWS])
        self.player = self.game.players.get(faction=Faction.CROWS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Ensure Cats do their setup first to have the keep
        self.game_setup = GameSimpleSetup.objects.get(game=self.game)
        self.game_setup.status = GameSimpleSetup.GameSetupStatus.CATS_SETUP
        self.game_setup.save()

        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        # Note: we manually set up Cats so we know where keep is
        pick_corner(self.cats_player, c1)

        # Move to Crows Setup status
        self.game_setup.status = GameSimpleSetup.GameSetupStatus.CROWS_SETUP
        self.game_setup.save()

        # Ensure Cats have a turn to avoid "No turns found" when setup fully completes
        from game.transactions.cats import create_cats_turn
        create_cats_turn(self.cats_player)

        # Initialize Crow setup
        try:
            self.crow_setup = CrowsSimpleSetup.objects.get(player=self.player)
        except CrowsSimpleSetup.DoesNotExist:
            self.crow_setup = start_simple_crows_setup(self.player)


class CrowSupplyCreationTests(CrowSetupBaseTestCase):
    def test_supply_created(self):
        # 15 warriors in supply (null clearing)
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing__isnull=True).count(), 15)
        # 8 plots created, 2 of each
        self.assertEqual(PlotToken.objects.filter(player=self.player).count(), 8)
        self.assertEqual(PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.BOMB).count(), 2)
        # Verify setup step is correct
        self.assertEqual(self.crow_setup.step, CrowsSimpleSetup.Steps.WARRIOR_PLACE)


class CrowPlaceWarriorTests(CrowSetupBaseTestCase):
    def test_place_warrior_success(self):
        # Find clearings
        fox_c = Clearing.objects.filter(game=self.game, suit=Suit.RED.value).exclude(clearing_number=1).first()
        rabbit_c = Clearing.objects.filter(game=self.game, suit=Suit.YELLOW.value).first()
        mouse_c = Clearing.objects.filter(game=self.game, suit=Suit.ORANGE.value).first()

        # Place in Fox
        place_initial_warrior(self.player, fox_c)
        self.assertEqual(Warrior.objects.filter(clearing=fox_c, player=self.player).count(), 1)
        self.crow_setup.refresh_from_db()
        self.assertTrue(self.crow_setup.fox_placed)
        self.assertFalse(self.crow_setup.rabbit_placed)
        self.assertEqual(self.crow_setup.step, CrowsSimpleSetup.Steps.WARRIOR_PLACE)

        # Place in Rabbit
        place_initial_warrior(self.player, rabbit_c)
        self.crow_setup.refresh_from_db()
        self.assertTrue(self.crow_setup.rabbit_placed)

        # Place in Mouse
        place_initial_warrior(self.player, mouse_c)
        self.crow_setup.refresh_from_db()
        self.assertTrue(self.crow_setup.mouse_placed)
        
        # Check transition to PENDING_CONFIRMATION
        self.assertEqual(self.crow_setup.step, CrowsSimpleSetup.Steps.PENDING_CONFIRMATION)
        
        # Verify logs
        self.assertLogExists(LogType.CROWS_SETUP_PLACE_WARRIOR, player=self.player, clearing_number=fox_c.clearing_number, suit=Suit.RED.value)
        self.assertLogExists(LogType.CROWS_SETUP_PLACE_WARRIOR, player=self.player, clearing_number=rabbit_c.clearing_number, suit=Suit.YELLOW.value)
        self.assertLogExists(LogType.CROWS_SETUP_PLACE_WARRIOR, player=self.player, clearing_number=mouse_c.clearing_number, suit=Suit.ORANGE.value)

    def test_place_warrior_duplicate_suit_fails(self):
        fox_c1 = Clearing.objects.filter(game=self.game, suit=Suit.RED.value).exclude(clearing_number=1).first()
        fox_c2 = Clearing.objects.filter(game=self.game, suit=Suit.RED.value).exclude(id=fox_c1.id).first()

        place_initial_warrior(self.player, fox_c1)
        with self.assertRaisesMessage(ValueError, "Fox clearing warrior already placed"):
            place_initial_warrior(self.player, fox_c2)

    def test_place_on_keep_fails(self):
        c1 = Clearing.objects.get(game=self.game, clearing_number=1) # The Keep is here
        with self.assertRaisesMessage(ValueError, "Cannot place in the keep clearing"):
            place_initial_warrior(self.player, c1)

    def test_place_wild_fails(self):
        c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        c2.suit = Suit.WILD.value
        c2.save()
        with self.assertRaisesMessage(ValueError, "Cannot place on a bird clearing during setup"):
            place_initial_warrior(self.player, c2)


class CrowConfirmSetupTests(CrowSetupBaseTestCase):
    def setUp(self):
        super().setUp()
        fox_c = Clearing.objects.filter(game=self.game, suit=Suit.RED.value).exclude(clearing_number=1).first()
        rabbit_c = Clearing.objects.filter(game=self.game, suit=Suit.YELLOW.value).first()
        mouse_c = Clearing.objects.filter(game=self.game, suit=Suit.ORANGE.value).first()
        place_initial_warrior(self.player, fox_c)
        place_initial_warrior(self.player, rabbit_c)
        place_initial_warrior(self.player, mouse_c)
        self.crow_setup.refresh_from_db()

    def test_confirm_completed_setup_success(self):
        confirm_completed_setup(self.player)
        self.crow_setup.refresh_from_db()
        self.assertEqual(self.crow_setup.step, CrowsSimpleSetup.Steps.COMPLETED)
        
        # Check that game status advanced
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, self.game.GameStatus.SETUP_COMPLETED)

    def test_confirm_completed_setup_wrong_step_fails(self):
        self.crow_setup.step = CrowsSimpleSetup.Steps.WARRIOR_PLACE
        self.crow_setup.save()

        with self.assertRaisesMessage(ValueError, "Setup not complete"):
            confirm_completed_setup(self.player)
