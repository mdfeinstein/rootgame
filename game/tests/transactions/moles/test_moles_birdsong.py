from django.test import TestCase

from game.models.game_models import Faction, Warrior
from game.models.moles.buildings import Citadel, Market
from game.models.moles.turn import MoleBirdsong, MoleTurn
from game.models.moles.burrow import Burrow
from game.tests.my_factories import GameSetupFactory
from game.transactions.moles.birdsong import place_burrow_warriors


class MolesBirdsongBaseTestCase(TestCase):
    def setUp(self):
        # GameSetupFactory now handles Moles setup correctly (burrow is created)
        self.game = GameSetupFactory(factions=[Faction.MOLES])
        self.player = self.game.players.get(faction=Faction.MOLES)

        # Get burrow that was created during setup
        self.burrow = Burrow.objects.get(player=self.player)

        # Create a turn for Moles (normally done by game flow)
        self.turn = MoleTurn.create_turn(self.player)
        self.birdsong = self.turn.birdsong.first()

        # Set birdsong to PLACE_WARRIORS step
        self.birdsong.step = MoleBirdsong.MoleBirdsongSteps.PLACE_WARRIORS
        self.birdsong.save()


class MolesBirdsongTests(MolesBirdsongBaseTestCase):
    def test_place_burrow_warriors_base(self):
        """With no buildings on map, place 1 warrior in burrow."""
        initial_supply = Warrior.objects.filter(player=self.player, clearing__isnull=True).count()
        initial_burrow = Warrior.objects.filter(player=self.player, clearing=self.burrow).count()

        place_burrow_warriors(self.player)

        final_supply = Warrior.objects.filter(player=self.player, clearing__isnull=True).count()
        final_burrow = Warrior.objects.filter(player=self.player, clearing=self.burrow).count()

        self.assertEqual(final_supply, initial_supply - 1)
        self.assertEqual(final_burrow, initial_burrow + 1)

    def test_place_burrow_warriors_with_1_building(self):
        """With 1 building on map (1 icon), place 2 warriors in burrow."""
        c2 = self.game.clearing_set.get(clearing_number=2)
        citadel = Citadel.objects.filter(player=self.player, building_slot__isnull=True).first()
        slot = c2.buildingslot_set.first()
        citadel.building_slot = slot
        citadel.save()

        initial_supply = Warrior.objects.filter(player=self.player, clearing__isnull=True).count()
        initial_burrow = Warrior.objects.filter(player=self.player, clearing=self.burrow).count()

        place_burrow_warriors(self.player)

        final_supply = Warrior.objects.filter(player=self.player, clearing__isnull=True).count()
        final_burrow = Warrior.objects.filter(player=self.player, clearing=self.burrow).count()

        self.assertEqual(final_supply, initial_supply - 2)
        self.assertEqual(final_burrow, initial_burrow + 2)

    def test_place_burrow_warriors_with_2_citadels(self):
        """With 2 citadels on map, place 1 + 3 = 4 warriors in burrow."""
        clearings = [
            self.game.clearing_set.get(clearing_number=2),
            self.game.clearing_set.get(clearing_number=3),
        ]
        buildings = [
            Citadel.objects.filter(player=self.player, building_slot__isnull=True).first(),
            Citadel.objects.filter(player=self.player, building_slot__isnull=True).first(),
        ]

        for i, clearing in enumerate(clearings):
            slot = clearing.buildingslot_set.first()
            buildings[i].building_slot = slot
            buildings[i].save()

        initial_supply = Warrior.objects.filter(player=self.player, clearing__isnull=True).count()
        initial_burrow = Warrior.objects.filter(player=self.player, clearing=self.burrow).count()

        place_burrow_warriors(self.player)

        final_supply = Warrior.objects.filter(player=self.player, clearing__isnull=True).count()
        final_burrow = Warrior.objects.filter(player=self.player, clearing=self.burrow).count()

        self.assertEqual(final_supply, initial_supply - 4)
        self.assertEqual(final_burrow, initial_burrow + 4)

    def test_place_burrow_warriors_supply_exhausted(self):
        """If fewer warriors in supply than needed, place only what's available."""
        # Place 2 citadels (would need 1 + 3 = 4 warriors)
        clearings = [
            self.game.clearing_set.get(clearing_number=2),
            self.game.clearing_set.get(clearing_number=3),
        ]
        buildings = [
            Citadel.objects.filter(player=self.player, building_slot__isnull=True).first(),
            Citadel.objects.filter(player=self.player, building_slot__isnull=True).first(),
        ]

        for i, clearing in enumerate(clearings):
            slot = clearing.buildingslot_set.first()
            buildings[i].building_slot = slot
            buildings[i].save()

        # Manually remove warriors from supply to leave only 2 available
        all_supply_warriors = list(Warrior.objects.filter(player=self.player, clearing__isnull=True))
        for warrior in all_supply_warriors[2:]:
            warrior.delete()

        initial_supply = Warrior.objects.filter(player=self.player, clearing__isnull=True).count()
        self.assertEqual(initial_supply, 2)

        place_burrow_warriors(self.player)

        final_supply = Warrior.objects.filter(player=self.player, clearing__isnull=True).count()
        final_burrow = Warrior.objects.filter(player=self.player, clearing=self.burrow).count()

        # Should place only the 2 available warriors
        self.assertEqual(final_supply, 0)
        self.assertEqual(final_burrow, 2)
