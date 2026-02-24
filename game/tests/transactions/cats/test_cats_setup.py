from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, BuildingSlot, Building
from game.models.cats.buildings import Recruiter, Sawmill, Workshop, CatBuildingTypes
from game.models.cats.tokens import CatKeep, CatWood
from game.models.cats.setup import CatsSimpleSetup
from game.models.events.setup import GameSimpleSetup
from game.tests.my_factories import GameSetupFactory
from game.transactions.cats_setup import pick_corner, place_initial_building, confirm_completed_setup, start_simple_cats_setup
from game.queries.general import determine_clearing_rule

class CatSetupBaseTestCase(TestCase):
    def setUp(self):
        # Create a game with Cats and Birds.
        # GameSetupFactory starts the game, which should trigger CATS_SETUP status.
        self.game = GameSetupFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.player = self.game.players.get(faction=Faction.CATS)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        
        # Ensure we are in Cats setup status
        self.game_setup = GameSimpleSetup.objects.get(game=self.game)
        self.game_setup.status = GameSimpleSetup.GameSetupStatus.CATS_SETUP
        self.game_setup.save()

        # Initialize Cat setup if not already done
        try:
            self.cat_setup = CatsSimpleSetup.objects.get(player=self.player)
        except CatsSimpleSetup.DoesNotExist:
            self.cat_setup = start_simple_cats_setup(self.player)

class CatPickCornerTests(CatSetupBaseTestCase):
    def test_pick_corner_success(self):
        # Corner clearings are 1, 2, 3, 4
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        
        pick_corner(self.player, c1)
        
        # Check Keep placement
        self.assertTrue(CatKeep.objects.filter(player=self.player, clearing=c1).exists())
        
        # Check Garrison placement: 1 warrior in every clearing except the opposite corner (3)
        clearings = Clearing.objects.filter(game=self.game)
        c3 = Clearing.objects.get(game=self.game, clearing_number=3)
        for c in clearings:
            if c.pk == c3.pk:
                self.assertEqual(Warrior.objects.filter(clearing=c, player=self.player).count(), 0)
            else:
                self.assertEqual(Warrior.objects.filter(clearing=c, player=self.player).count(), 1)
        # Check setup step advancement
        self.cat_setup.refresh_from_db()
        self.assertEqual(self.cat_setup.step, CatsSimpleSetup.Steps.PLACING_BUILDINGS)

    def test_pick_corner_invalid_fails(self):
        # C5 is not a corner clearing
        c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        
        with self.assertRaisesMessage(ValueError, "Clearing is not a corner clearing"):
            pick_corner(self.player, c5)

    def test_pick_corner_wrong_step_fails(self):
        self.cat_setup.step = CatsSimpleSetup.Steps.PLACING_BUILDINGS
        self.cat_setup.save()
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        
        with self.assertRaisesMessage(ValueError, "Wrong step"):
            pick_corner(self.player, c1)

class CatPlaceBuildingTests(CatSetupBaseTestCase):
    def setUp(self):
        super().setUp()
        # Initialize to PLACING_BUILDINGS step
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        pick_corner(self.player, self.c1)
        self.cat_setup.refresh_from_db()

    def test_place_initial_building_success(self):
        # Place Workshop in C1 (Keep clearing)
        slot1 = BuildingSlot.objects.filter(clearing=self.c1, building=None).first()
        place_initial_building(self.player, self.c1, CatBuildingTypes.WORKSHOP)
        self.assertTrue(Workshop.objects.filter(building_slot=slot1).exists())
        
        # Place Sawmill in C5 (Adjacent)
        c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        slot5 = BuildingSlot.objects.filter(clearing=c5, building=None).first()
        place_initial_building(self.player, c5, CatBuildingTypes.SAWMILL)
        self.assertTrue(Sawmill.objects.filter(building_slot=slot5).exists())
        
        # Place Recruiter in C10 (Adjacent)
        c10 = Clearing.objects.get(game=self.game, clearing_number=10)
        slot10 = BuildingSlot.objects.filter(clearing=c10, building=None).first()
        place_initial_building(self.player, c10, CatBuildingTypes.RECRUITER)
        self.assertTrue(Recruiter.objects.filter(building_slot=slot10).exists())
        
        # Check setup step advancement
        self.cat_setup.refresh_from_db()
        self.assertTrue(self.cat_setup.workshop_placed)
        self.assertTrue(self.cat_setup.sawmill_placed)
        self.assertTrue(self.cat_setup.recruiter_placed)
        self.assertEqual(self.cat_setup.step, CatsSimpleSetup.Steps.PENDING_CONFIRMATION)

    def test_place_duplicate_type_fails(self):
        place_initial_building(self.player, self.c1, CatBuildingTypes.WORKSHOP)
        
        with self.assertRaisesMessage(ValueError, "Building (Workshop) has already been placed"):
            place_initial_building(self.player, self.c1, CatBuildingTypes.WORKSHOP)

    def test_place_not_adjacent_fails(self):
        # C3 is not adjacent to C1
        c3 = Clearing.objects.get(game=self.game, clearing_number=3)
        
        with self.assertRaisesMessage(ValueError, "Clearing is not adjacent to the keep"):
            place_initial_building(self.player, c3, CatBuildingTypes.WORKSHOP)

    def test_place_wrong_step_fails(self):
        # Reset to PICKING_CORNER
        self.cat_setup.step = CatsSimpleSetup.Steps.PICKING_CORNER
        self.cat_setup.save()
        
        with self.assertRaisesMessage(ValueError, "Wrong step"):
            place_initial_building(self.player, self.c1, CatBuildingTypes.WORKSHOP)

class CatConfirmSetupTests(CatSetupBaseTestCase):
    def setUp(self):
        super().setUp()
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        pick_corner(self.player, self.c1)
        place_initial_building(self.player, self.c1, CatBuildingTypes.WORKSHOP)
        c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        place_initial_building(self.player, c5, CatBuildingTypes.SAWMILL)
        c10 = Clearing.objects.get(game=self.game, clearing_number=10)
        place_initial_building(self.player, c10, CatBuildingTypes.RECRUITER)
        self.cat_setup.refresh_from_db()

    def test_confirm_completed_setup_success(self):
        confirm_completed_setup(self.player)
        
        self.cat_setup.refresh_from_db()
        self.assertEqual(self.cat_setup.step, CatsSimpleSetup.Steps.COMPLETED)
        
        self.game_setup.refresh_from_db()
        self.assertEqual(self.game_setup.status, GameSimpleSetup.GameSetupStatus.BIRDS_SETUP)
        
        # Check that first turn was created
        from game.models import CatTurn
        self.assertTrue(CatTurn.objects.filter(player=self.player).exists())

    def test_confirm_completed_setup_wrong_step_fails(self):
        # Revert one building to break requirements
        self.cat_setup.workshop_placed = False
        self.cat_setup.step = CatsSimpleSetup.Steps.PLACING_BUILDINGS
        self.cat_setup.save()
        
        # Workshop level 1 has cost 0, but Sawmill/Recruiter cost 0 too.
        # Actually place_initial_building doesn't care about wood, it's setup.
        
        with self.assertRaisesMessage(ValueError, "Setup not complete"):
            confirm_completed_setup(self.player)

