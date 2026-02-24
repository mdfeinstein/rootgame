from django.test import TestCase
from game.models.game_models import Game, Faction, Clearing, Warrior, Building
from game.models.cats.setup import CatsSimpleSetup
from game.models.cats.tokens import CatKeep
from game.models.events.setup import GameSimpleSetup
from game.models.birds.setup import BirdsSimpleSetup
from game.models.birds.player import BirdLeader
from game.tests.my_factories import GameSetupFactory, UserFactory
from game.tests.client import RootGameClient
from rest_framework import status


class SetupUndoTests(TestCase):
    def setUp(self):
        # Create a game with Cats and Birds. GameSetupFactory starts the game.
        self.owner = UserFactory(username="owner")
        self.owner.set_password("password")
        self.owner.save()
        self.user2 = UserFactory(username="user2")
        self.user2.set_password("password")
        self.user2.save()
        self.game = GameSetupFactory(
            owner=self.owner,
            users=[self.owner, self.user2],
            factions=[Faction.CATS, Faction.BIRDS],
        )
        self.cats_client = RootGameClient("owner", "password", self.game.id)
        self.birds_client = RootGameClient("user2", "password", self.game.id)

    def test_cats_setup_undo(self):
        # Initial state: Cats setup should be in PICKING_CORNER
        cats_player = self.game.players.get(faction=Faction.CATS)
        cats_setup = CatsSimpleSetup.objects.get(player=cats_player)
        self.assertEqual(cats_setup.step, CatsSimpleSetup.Steps.PICKING_CORNER)

        # 1. Cats Pick Corner (Clearing 1)
        self.cats_client.get_action()
        response = self.cats_client.submit_action({"clearing_number": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        cats_setup.refresh_from_db()
        self.assertEqual(cats_setup.step, CatsSimpleSetup.Steps.PLACING_BUILDINGS)
        self.assertTrue(
            CatKeep.objects.filter(
                player=cats_player, clearing__clearing_number=1
            ).exists()
        )
        # Garrison should be placed (11 warriors in other clearings)
        self.assertEqual(
            Warrior.objects.filter(player=cats_player, clearing__isnull=False).count(),
            11,
        )

        # 2. Undo Pick Corner
        undo_response = self.cats_client.post(f"/api/game/undo/{self.game.id}/")
        self.assertEqual(undo_response.status_code, status.HTTP_200_OK)

        cats_setup.refresh_from_db()
        self.assertEqual(cats_setup.step, CatsSimpleSetup.Steps.PICKING_CORNER)
        self.assertFalse(
            CatKeep.objects.filter(player=cats_player, clearing__isnull=False).exists()
        )
        self.assertEqual(
            Warrior.objects.filter(player=cats_player, clearing__isnull=False).count(),
            0,
        )

    def test_cats_place_building_undo(self):
        cats_player = self.game.players.get(faction=Faction.CATS)

        # 1. Pick Corner (Clearing 1)
        self.cats_client.get_action()
        self.cats_client.submit_action({"clearing_number": 1})

        # 2. Place Building (Clearing 1 is adjacent to the Keep in 1)
        self.cats_client.get_action()
        # Step 1: Select clearing
        self.cats_client.submit_action({"clearing_number": 1})
        # Step 2: Select building type
        response = self.cats_client.submit_action({"building_type": "SAWMILL"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        cats_setup = CatsSimpleSetup.objects.get(player=cats_player)
        self.assertTrue(cats_setup.sawmill_placed)
        self.assertTrue(
            Building.objects.filter(
                player=cats_player, building_slot__clearing__clearing_number=1
            ).exists()
        )

        # 3. Undo Place Building
        undo_response = self.cats_client.post(f"/api/game/undo/{self.game.id}/")
        self.assertEqual(undo_response.status_code, status.HTTP_200_OK)

        cats_setup.refresh_from_db()
        self.assertFalse(cats_setup.sawmill_placed)
        # Building should be back in player's supply (null building_slot)
        self.assertFalse(
            Building.objects.filter(
                player=cats_player, building_slot__isnull=False
            ).exists()
        )

    def test_birds_setup_undo(self):
        cats_player = self.game.players.get(faction=Faction.CATS)
        birds_player = self.game.players.get(faction=Faction.BIRDS)

        # Complete Cats setup to move to Birds
        self.cats_client.get_action()
        self.cats_client.submit_action({"clearing_number": 1})  # Corner 1

        # Place 3 buildings
        for cl, bt in [(1, "SAWMILL"), (5, "WORKSHOP"), (9, "RECRUITER")]:
            self.cats_client.get_action()
            self.cats_client.submit_action({"clearing_number": cl})
            self.cats_client.submit_action({"building_type": bt})

        # Confirm Cats Setup (undoable=False, but we haven't reached it yet)
        self.cats_client.get_action()
        self.cats_client.submit_action({"confirm": True})

        # Birds Setup starts
        birds_setup = BirdsSimpleSetup.objects.get(player=birds_player)
        self.assertEqual(birds_setup.step, BirdsSimpleSetup.Steps.PICKING_CORNER)

        # 1. Birds Pick Corner (Opposite to Cats' Keep in 1 is 3)
        self.birds_client.get_action()
        response = self.birds_client.submit_action({"clearing_number": 3})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        birds_setup.refresh_from_db()
        self.assertEqual(birds_setup.step, BirdsSimpleSetup.Steps.CHOOSING_LEADER)

        # 2. Undo Birds Corner
        undo_response = self.birds_client.post(f"/api/game/undo/{self.game.id}/")
        self.assertEqual(undo_response.status_code, status.HTTP_200_OK)

        birds_setup.refresh_from_db()
        self.assertEqual(birds_setup.step, BirdsSimpleSetup.Steps.PICKING_CORNER)

    def test_failed_undo_across_confirmed_setup(self):
        cats_player = self.game.players.get(faction=Faction.CATS)

        # Complete Cats setup
        self.cats_client.get_action()
        self.cats_client.submit_action({"clearing_number": 1})
        for cl, bt in [(1, "SAWMILL"), (5, "WORKSHOP"), (9, "RECRUITER")]:
            self.cats_client.get_action()
            self.cats_client.submit_action({"clearing_number": cl})
            self.cats_client.submit_action({"building_type": bt})

        # Confirm (undoable=False in atomic_game_action)
        self.cats_client.get_action()
        self.cats_client.submit_action({"confirm": True})

        # Try to undo Cats confirmation from Birds' turn
        # Birds' first action should be picking a corner.
        # If we undo, it should either fail OR just do nothing if there are no undoable actions in the current checkpoint.
        # Actually, when Cats confirm, a NEW checkpoint is created because it's undoable=False.
        # So the new checkpoint for the game has NO actions yet.

        undo_response = self.birds_client.post(f"/api/game/undo/{self.game.id}/")
        # should return 200 but not change anything if no actions to undo
        self.assertEqual(undo_response.status_code, status.HTTP_200_OK)

        cats_setup = CatsSimpleSetup.objects.get(player=cats_player)
        self.assertEqual(cats_setup.step, CatsSimpleSetup.Steps.COMPLETED)

    def test_birds_choose_leader_undo(self):
        birds_player = self.game.players.get(faction=Faction.BIRDS)

        # Complete Cats setup to move to Birds
        self.cats_client.get_action()
        self.cats_client.submit_action({"clearing_number": 1})
        for cl, bt in [(1, "SAWMILL"), (5, "WORKSHOP"), (9, "RECRUITER")]:
            self.cats_client.get_action()
            self.cats_client.submit_action({"clearing_number": cl})
            self.cats_client.submit_action({"building_type": bt})
        self.cats_client.get_action()
        self.cats_client.submit_action({"confirm": True})

        # Birds Pick Corner
        self.birds_client.get_action()
        self.birds_client.submit_action({"clearing_number": 3})

        # Birds Choose Leader
        self.birds_client.get_action()
        response = self.birds_client.submit_action({"leader": "DESPOT"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            BirdLeader.objects.filter(
                player=birds_player, leader=BirdLeader.BirdLeaders.DESPOT
            ).exists()
        )
        birds_setup = BirdsSimpleSetup.objects.get(player=birds_player)
        self.assertEqual(birds_setup.step, BirdsSimpleSetup.Steps.PENDING_CONFIRMATION)

        # Undo Leader Selection
        undo_response = self.birds_client.post(f"/api/game/undo/{self.game.id}/")
        self.assertEqual(undo_response.status_code, status.HTTP_200_OK)

        # Leaders should still exist (created at start of birds setup) but none should be active
        self.assertFalse(
            BirdLeader.objects.filter(player=birds_player, active=True).exists()
        )
        from game.models.birds.player import Vizier

        self.assertFalse(Vizier.objects.filter(player=birds_player).exists())

        birds_setup.refresh_from_db()
        self.assertEqual(birds_setup.step, BirdsSimpleSetup.Steps.CHOOSING_LEADER)
