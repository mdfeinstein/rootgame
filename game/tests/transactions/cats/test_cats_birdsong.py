from django.test import TestCase
from game.models.game_models import Faction, Clearing, BuildingSlot
from game.models.cats.buildings import Sawmill
from game.models.cats.tokens import CatWood
from game.models.cats.turn import CatBirdsong
from game.tests.my_factories import GameSetupWithFactionsFactory, CatWoodFactory
from game.transactions.cats import cat_produce_all_wood, produce_wood

class CatBirdsongBaseTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.player = self.game.players.get(faction=Faction.CATS)
        
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1) # Fox (Cat Keep / Sawmill)
        self.c5 = Clearing.objects.get(game=self.game, clearing_number=5) # Rabbit (Workshop)
        self.c9 = Clearing.objects.get(game=self.game, clearing_number=9) # Mouse (Recruiter)

        self.turn = CatBirdsong.objects.get(turn__player=self.player).turn
        self.birdsong = self.turn.birdsong
        self.birdsong.step = CatBirdsong.CatBirdsongSteps.PLACING_WOOD
        self.birdsong.save()

        # Factories might have already placed wood. Clear it for clean testing.
        CatWood.objects.filter(player=self.player).update(clearing=None)
        Sawmill.objects.filter(player=self.player).update(used=False)


class CatWoodPlacementTests(CatBirdsongBaseTestCase):
    def test_auto_wood_placement(self):
        # By default, setup places 1 sawmill in C1.
        # CatWood supply should have 8 tokens (from setup).
        # Calling cat_produce_all_wood should place wood in C1.
        initial_wood_in_c1 = CatWood.objects.filter(clearing=self.c1).count()
        
        cat_produce_all_wood(self.player)
        
        self.assertEqual(CatWood.objects.filter(clearing=self.c1).count(), initial_wood_in_c1 + 1)
        self.assertTrue(Sawmill.objects.filter(player=self.player, building_slot__clearing=self.c1).first().used)
        
        # Verify it transitions to next phase if all sawmills used
        self.birdsong.refresh_from_db()
        # next_step(player) for Birdsong COMPLETED calls step_effect(player, None) 
        # which might transition to Daylight CRAFTING.
        from game.models.cats.turn import CatDaylight
        daylight = CatDaylight.objects.get(turn=self.turn)
        self.assertEqual(daylight.step, CatDaylight.CatDaylightSteps.CRAFTING)

    def test_manual_wood_placement_low_supply(self):
        # Empty the supply
        CatWood.objects.filter(player=self.player, clearing=None).delete()
        # Add only ONE wood token to supply
        CatWoodFactory(player=self.player, clearing=None)
        
        # Add a second sawmill so supply (1) < sawmills (2)
        slot5 = BuildingSlot.objects.filter(clearing=self.c5, building=None).first()
        s2 = Sawmill.objects.filter(player=self.player, building_slot=None).first()
        s2.building_slot = slot5
        s2.save()
        
        # Now cat_produce_all_wood should probably fail or handle it.
        # Based on produce_wood logic, it places until all used or supply empty.
        # But if we want to test MANUALLY choosing where to put the limited wood:
        # We call produce_wood directly for the chosen sawmill.
        
        produce_wood(self.player, s2)
        
        self.assertTrue(s2.refresh_from_db() or s2.used)
        self.assertEqual(CatWood.objects.filter(clearing=self.c5).count(), 1)
        
        # Birdsong should still be in PLACING_WOOD because s1 (in C1) is not used.
        self.birdsong.refresh_from_db()
        self.assertEqual(self.birdsong.step, CatBirdsong.CatBirdsongSteps.PLACING_WOOD)
