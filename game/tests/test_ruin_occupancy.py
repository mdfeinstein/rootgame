from django.test import TestCase
from game.models.game_models import (
    Game,
    Faction,
    Clearing,
    Building,
    Ruin,
    BuildingSlot,
)
from game.models.cats.buildings import CatBuildingTypes, Workshop
from game.transactions.cats_setup import place_initial_building, start_simple_cats_setup
from game.tests.my_factories import GameSetupFactory, UserFactory
from game.models.cats.setup import CatsSimpleSetup


class RuinOccupancyTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        # GameSetupFactory(tx_start_game(game)) calls create_game_setup, map_setup, begin_faction_setup
        # map_setup(autumn) creates ruins in clearings 6, 10, 11, 12
        self.game = GameSetupFactory(
            owner=self.user, factions=[Faction.CATS, Faction.BIRDS]
        )
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        # Place Keep in Clearing 1 (Corner)
        from game.transactions.cats_setup import pick_corner

        clearing_1 = Clearing.objects.get(game=self.game, clearing_number=1)
        pick_corner(self.cats_player, clearing_1)

        # ensure cats setup is now at PLACING_BUILDINGS
        self.cats_setup = CatsSimpleSetup.objects.get(player=self.cats_player)
        self.assertEqual(self.cats_setup.step, CatsSimpleSetup.Steps.PLACING_BUILDINGS)

    def test_cats_cannot_build_in_clearing_full_of_ruins_and_buildings(self):
        # Clearing 10 is adjacent to Clearing 1 (Keep)
        # Clearing 10 has 2 slots. In autumn_map_setup, one is a ruin (idx 9).
        clearing_10 = Clearing.objects.get(game=self.game, clearing_number=10)
        slots = BuildingSlot.objects.filter(clearing=clearing_10)
        self.assertEqual(slots.count(), 2)

        # Verify one is a ruin
        ruins = Ruin.objects.filter(building_slot__clearing=clearing_10)
        self.assertEqual(ruins.count(), 1)

        # Manually fill the other slot with a building
        free_slot = slots.exclude(ruin__isnull=False).first()
        Building.objects.create(player=self.cats_player, building_slot=free_slot)

        # Now clearing 10 should be full
        with self.assertRaisesRegex(ValueError, "No free building slots"):
            place_initial_building(
                self.cats_player, clearing_10, CatBuildingTypes.WORKSHOP
            )

    def test_cats_can_build_if_slots_available_despite_ruins(self):
        # Clearing 10 is adjacent to Clearing 1 (Keep)
        clearing_10 = Clearing.objects.get(game=self.game, clearing_number=10)
        slots = BuildingSlot.objects.filter(clearing=clearing_10)
        self.assertEqual(slots.count(), 2)

        ruins = Ruin.objects.filter(building_slot__clearing=clearing_10)
        self.assertEqual(ruins.count(), 1)

        # Placing a building should succeed because 1 slot is free
        place_initial_building(self.cats_player, clearing_10, CatBuildingTypes.WORKSHOP)
        self.cats_setup.refresh_from_db()
        self.assertTrue(self.cats_setup.workshop_placed)
