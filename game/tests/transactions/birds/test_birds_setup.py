from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, BuildingSlot, Building
from game.models.birds.buildings import BirdRoost
from game.models.birds.player import BirdLeader, Vizier
from game.models.birds.setup import BirdsSimpleSetup
from game.models.events.setup import GameSimpleSetup
from game.models.cats.tokens import CatKeep
from game.tests.my_factories import GameSetupFactory, PlayerFactory
from game.transactions.birds_setup import pick_corner, choose_leader_initial, confirm_completed_setup, start_simple_birds_setup

class BirdSetupBaseTestCase(TestCase):
    def setUp(self):
        # Create a game with Cats and Birds by default
        self.game = GameSetupFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Ensure we are in Birds setup status
        self.game_setup = GameSimpleSetup.objects.get(game=self.game)
        self.game_setup.status = GameSimpleSetup.GameSetupStatus.BIRDS_SETUP
        self.game_setup.save()

        # Initialize Bird setup
        try:
            self.bird_setup = BirdsSimpleSetup.objects.get(player=self.player)
        except BirdsSimpleSetup.DoesNotExist:
            self.bird_setup = start_simple_birds_setup(self.player)

class BirdPickCornerTests(BirdSetupBaseTestCase):
    def test_pick_corner_success_with_cats(self):
        # Update existing Cat Keep in C1
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        keep = CatKeep.objects.get(player=self.cats_player)
        keep.clearing = c1
        keep.save()
        
        # Birds must pick opposite corner: C3
        c3 = Clearing.objects.get(game=self.game, clearing_number=3)
        pick_corner(self.player, c3)
        
        # Check Roost placement
        self.assertTrue(BirdRoost.objects.filter(building_slot__clearing=c3).exists())
        
        # Check 6 warriors placement
        self.assertEqual(Warrior.objects.filter(clearing=c3, player=self.player).count(), 6)
        
        # Check setup step advancement
        self.bird_setup.refresh_from_db()
        self.assertEqual(self.bird_setup.step, BirdsSimpleSetup.Steps.CHOOSING_LEADER)

    def test_pick_corner_invalid_with_cats_fails(self):
        # Update existing Cat Keep in C1
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        keep = CatKeep.objects.get(player=self.cats_player)
        keep.clearing = c1
        keep.save()
        
        # Birds try to pick a different corner (C2)
        c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        with self.assertRaisesMessage(ValueError, "Cat's Keep is not in the opposite corner"):
            pick_corner(self.player, c2)

    def test_pick_corner_success_without_cats(self):
        # Create a game with ONLY Birds (or no Cats with Keep)
        game_no_cats = GameSetupFactory(factions=[Faction.BIRDS])
        player = game_no_cats.players.get(faction=Faction.BIRDS)
        
        game_setup = GameSimpleSetup.objects.get(game=game_no_cats)
        game_setup.status = GameSimpleSetup.GameSetupStatus.BIRDS_SETUP
        game_setup.save()
        
        # Setup already exists
        bird_setup = BirdsSimpleSetup.objects.get(player=player)
        
        # Any corner should work
        c1 = Clearing.objects.get(game=game_no_cats, clearing_number=1)
        pick_corner(player, c1)
        
        self.assertEqual(Warrior.objects.filter(clearing=c1, player=player).count(), 6)
        bird_setup.refresh_from_db()
        self.assertEqual(bird_setup.step, BirdsSimpleSetup.Steps.CHOOSING_LEADER)


    def test_pick_non_corner_fails(self):
        c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        with self.assertRaisesMessage(ValueError, "Clearing number must be 1, 2, 3, or 4 to be a corner"):
            pick_corner(self.player, c5)

class BirdChooseLeaderTests(BirdSetupBaseTestCase):
    def setUp(self):
        super().setUp()
        # Advance to choosing leader
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        # Without cats' keep, any corner works
        pick_corner(self.player, c1)
        self.bird_setup.refresh_from_db()

    def test_choose_leader_builder_viziers(self):
        choose_leader_initial(self.player, BirdLeader.BirdLeaders.BUILDER)
        
        self.assertTrue(BirdLeader.objects.get(player=self.player, leader=BirdLeader.BirdLeaders.BUILDER).active)
        # Builder: Recruit, Move
        self.assertTrue(Vizier.objects.filter(player=self.player, column=Vizier.Column.RECRUIT).exists())
        self.assertTrue(Vizier.objects.filter(player=self.player, column=Vizier.Column.MOVE).exists())
        self.assertEqual(Vizier.objects.filter(player=self.player).count(), 2)
        
        self.bird_setup.refresh_from_db()
        self.assertEqual(self.bird_setup.step, BirdsSimpleSetup.Steps.PENDING_CONFIRMATION)

    def test_choose_leader_charismatic_viziers(self):
        choose_leader_initial(self.player, BirdLeader.BirdLeaders.CHARISMATIC)
        # Charismatic: Recruit, Battle
        self.assertTrue(Vizier.objects.filter(player=self.player, column=Vizier.Column.RECRUIT).exists())
        self.assertTrue(Vizier.objects.filter(player=self.player, column=Vizier.Column.BATTLE).exists())
        self.assertEqual(Vizier.objects.filter(player=self.player).count(), 2)

    def test_choose_leader_commander_viziers(self):
        choose_leader_initial(self.player, BirdLeader.BirdLeaders.COMMANDER)
        # Commander: Move, Battle
        self.assertTrue(Vizier.objects.filter(player=self.player, column=Vizier.Column.MOVE).exists())
        self.assertTrue(Vizier.objects.filter(player=self.player, column=Vizier.Column.BATTLE).exists())
        self.assertEqual(Vizier.objects.filter(player=self.player).count(), 2)

    def test_choose_leader_despot_viziers(self):
        choose_leader_initial(self.player, BirdLeader.BirdLeaders.DESPOT)
        # Despot: Move, Build
        self.assertTrue(Vizier.objects.filter(player=self.player, column=Vizier.Column.MOVE).exists())
        self.assertTrue(Vizier.objects.filter(player=self.player, column=Vizier.Column.BUILD).exists())
        self.assertEqual(Vizier.objects.filter(player=self.player).count(), 2)

class BirdConfirmSetupTests(BirdSetupBaseTestCase):
    def setUp(self):
        super().setUp()
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        pick_corner(self.player, c1)
        choose_leader_initial(self.player, BirdLeader.BirdLeaders.DESPOT)
        self.bird_setup.refresh_from_db()
        
        # Ensure Cats have a turn created so next_player_setup doesn't crash
        from game.transactions.cats import create_cats_turn
        create_cats_turn(self.cats_player)

    def test_confirm_completed_setup_success(self):
        confirm_completed_setup(self.player)
        
        self.bird_setup.refresh_from_db()
        self.assertEqual(self.bird_setup.step, BirdsSimpleSetup.Steps.COMPLETED)
        
        # Check that first turn was created
        from game.models.birds.turn import BirdTurn
        self.assertTrue(BirdTurn.objects.filter(player=self.player).exists())

