from django.test import TestCase
from game.tests.my_factories import GameSetupWithFactionsFactory
from game.models.game_models import Faction, Warrior, Clearing
from game.models.cats.buildings import Recruiter, Sawmill, Workshop
from game.models.cats.tokens import CatKeep, CatWood
from game.models.birds.buildings import BirdRoost
from game.models.wa.tokens import WASympathy
from game.transactions.general import (
    place_piece_from_supply_into_clearing,
    place_warriors_into_clearing,
)
from game.transactions.birds import place_roost
from game.transactions.wa import place_sympathy


class PiecePlacementTests(TestCase):
    def setUp(self):
        # GameSetupWithFactionsFactory sets up Cats, Birds, and WA
        # Clearing 1 (fox) has the Keep
        # Clearing 3 (rabbit) has the Roost
        self.game = GameSetupWithFactionsFactory(
            factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE]
        )
        self.player_cats = self.game.players.get(faction=Faction.CATS)
        self.player_birds = self.game.players.get(faction=Faction.BIRDS)
        self.player_wa = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)

        self.clearing_keep = Clearing.objects.get(game=self.game, clearing_number=1)
        self.clearing_no_keep = Clearing.objects.get(game=self.game, clearing_number=2)

    def test_cats_can_place_in_keep(self):
        # Cat warrior
        warrior = Warrior.objects.filter(player=self.player_cats, clearing=None).first()
        place_piece_from_supply_into_clearing(warrior, self.clearing_keep)
        self.assertEqual(warrior.clearing, self.clearing_keep)

        # Cat wood
        wood = CatWood.objects.filter(player=self.player_cats, clearing=None).first()
        place_piece_from_supply_into_clearing(wood, self.clearing_keep)
        self.assertEqual(wood.clearing, self.clearing_keep)

        # Cat building (Recruiter)
        # Clearing 1 already has a sawmill from factory setup, but it has 1 slot (Fox, clearing 1)
        # Wait, if clearing 1 has 1 slot and it's filled by a sawmill, I need another slot.
        # Let's check slot count for clearing 1 in autumn_map_setup:
        # slot_counts = [1, 2, 1, 1, 2, 2, 2, 2, 2, 2, 3, 2]
        # Clearing 1 has only 1 slot.
        # Factory setup places a sawmill in clearing 1.
        # So I'll use clearing 5 (rabbit) which has 2 slots.
        clearing_5 = Clearing.objects.get(game=self.game, clearing_number=5)
        # It has a workshop. Let's add a recruiter there.
        recruiter = Recruiter.objects.filter(
            player=self.player_cats, building_slot=None
        ).first()
        place_piece_from_supply_into_clearing(recruiter, clearing_5)
        self.assertEqual(recruiter.clearing, clearing_5)

    def test_non_cats_blocked_in_keep(self):
        # Bird warrior
        bird_warrior = Warrior.objects.filter(
            player=self.player_birds, clearing=None
        ).first()
        with self.assertRaises(ValueError) as cm:
            place_piece_from_supply_into_clearing(bird_warrior, self.clearing_keep)
        self.assertIn("keep clearing", str(cm.exception))

        # WA sympathy
        wa_sympathy = WASympathy.objects.filter(
            player=self.player_wa, clearing=None
        ).first()
        with self.assertRaises(ValueError) as cm:
            place_piece_from_supply_into_clearing(wa_sympathy, self.clearing_keep)
        self.assertIn("keep clearing", str(cm.exception))

    def test_integrated_placed_warriors_into_clearing(self):
        # Cats placing 3 warriors in Keep
        initial_count = Warrior.objects.filter(
            player=self.player_cats, clearing=self.clearing_keep
        ).count()
        place_warriors_into_clearing(self.player_cats, self.clearing_keep, 3)
        final_count = Warrior.objects.filter(
            player=self.player_cats, clearing=self.clearing_keep
        ).count()
        self.assertEqual(final_count, initial_count + 3)

        # Birds placing 1 warrior in Keep (should fail)
        with self.assertRaises(ValueError):
            place_warriors_into_clearing(self.player_birds, self.clearing_keep, 1)

    def test_integrated_place_roost(self):
        # Birds trying to place roost in keep clearing
        with self.assertRaises(ValueError) as cm:
            place_roost(self.player_birds, self.clearing_keep)
        self.assertIn("keep clearing", str(cm.exception))

        # Should work in non-keep clearing with slot
        # Clearing 2 has 2 slots and is empty
        place_roost(self.player_birds, self.clearing_no_keep)
        self.assertTrue(
            BirdRoost.objects.filter(
                player=self.player_birds, building_slot__clearing=self.clearing_no_keep
            ).exists()
        )

    def test_integrated_place_sympathy(self):
        # WA trying to place sympathy in keep clearing
        with self.assertRaises(ValueError) as cm:
            place_sympathy(self.player_wa, self.clearing_keep)
        self.assertIn("keep clearing", str(cm.exception))

        # Should work in non-keep clearing
        place_sympathy(self.player_wa, self.clearing_no_keep)
        self.assertTrue(
            WASympathy.objects.filter(
                player=self.player_wa, clearing=self.clearing_no_keep
            ).exists()
        )

    def test_placement_fails_if_already_on_board(self):
        cat_warrior = Warrior.objects.filter(
            player=self.player_cats, clearing=None
        ).first()
        place_piece_from_supply_into_clearing(cat_warrior, self.clearing_no_keep)

        with self.assertRaises(ValueError) as cm:
            place_piece_from_supply_into_clearing(cat_warrior, self.clearing_keep)
        self.assertEqual(str(cm.exception), "piece is already in a clearing")
