from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, BuildingSlot, HandEntry, Building
from game.queries.general import determine_clearing_rule
from game.models.cats.buildings import Recruiter, Sawmill, Workshop, CatBuildingTypes
from game.models.cats.tokens import CatWood
from game.models.cats.turn import CatDaylight, CatBirdsong
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, WarriorFactory, CatWoodFactory
from game.transactions.cats import cat_recruit, cat_build, overwork, cat_recruit_all, cat_march, birds_for_hire, cat_craft_card, end_action_step
from game.game_data.cards.exiles_and_partisans import CardsEP

class CatBaseTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.player = self.game.players.get(faction=Faction.CATS)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1) # Fox (Cat Keep / Sawmill)
        self.c5 = Clearing.objects.get(game=self.game, clearing_number=5) # Rabbit (Workshop)
        self.c9 = Clearing.objects.get(game=self.game, clearing_number=9) # Mouse (Recruiter)

        # Standardise state for Daylight Actions
        self.turn = CatDaylight.objects.get(turn__player=self.player).turn
        birdsong = self.turn.birdsong
        birdsong.step = birdsong.CatBirdsongSteps.COMPLETED
        birdsong.save()

        self.daylight = self.turn.daylight
        self.daylight.step = CatDaylight.CatDaylightSteps.ACTIONS
        self.daylight.actions_left = 3
        self.daylight.save()

class CatRecruitTests(CatBaseTestCase):
    def test_recruit_all(self):
        # Recruiter in 9. Add another in 5.
        slot = BuildingSlot.objects.filter(clearing=self.c5, building=None).first()
        r2 = Recruiter.objects.filter(player=self.player, building_slot=None).first()
        r2.building_slot = slot
        r2.save()
        
        initial_w9 = Warrior.objects.filter(player=self.player, clearing=self.c9).count()
        initial_w5 = Warrior.objects.filter(player=self.player, clearing=self.c5).count()
        
        cat_recruit_all(self.player)
        
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=self.c9).count(), initial_w9 + 1)
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=self.c5).count(), initial_w5 + 1)
        self.assertTrue(self.daylight.refresh_from_db() or self.daylight.recruit_used)

    def test_recruit_no_actions_fails(self):
        self.daylight.actions_left = 0
        self.daylight.save()
        all_on_board = Recruiter.objects.filter(player=self.player, building_slot__isnull=False)
        
        with self.assertRaisesMessage(ValueError, "No actions remaining"):
            cat_recruit(self.player, all_on_board)

    def test_recruit_already_used_fails(self):
        self.daylight.recruit_used = True
        self.daylight.save()
        all_on_board = Recruiter.objects.filter(player=self.player, building_slot__isnull=False)
        
        with self.assertRaisesMessage(ValueError, "Recruit has already been used this turn"):
            cat_recruit(self.player, all_on_board)

    def test_recruit_no_recruiters_fails(self):
        Recruiter.objects.filter(player=self.player).update(building_slot=None)
        
        with self.assertRaisesMessage(ValueError, "No recruiters selected to recruit from"):
            cat_recruit_all(self.player)

    def test_recruit_no_warriors_supply_fails(self):
        Warrior.objects.filter(player=self.player, clearing=None).delete()
        all_on_board = Recruiter.objects.filter(player=self.player, building_slot__isnull=False)
        
        with self.assertRaisesMessage(ValueError, "Not enough warriors in supply"):
            cat_recruit(self.player, all_on_board)

    def test_recruit_success_updates_state(self):
        target_recruiter = Recruiter.objects.filter(player=self.player, building_slot__isnull=False)
        cat_recruit(self.player, target_recruiter)
        
        self.daylight.refresh_from_db()
        self.assertTrue(self.daylight.recruit_used)
        self.assertEqual(self.daylight.actions_left, 2)
        self.assertTrue(target_recruiter.first().used)

class CatBuildTests(CatBaseTestCase):
    def test_build_workshop_success(self):
        wood = CatWoodFactory(player=self.player, clearing=self.c1)
        slot = BuildingSlot.objects.filter(clearing=self.c9, building=None).first()
        
        cat_build(self.player, CatBuildingTypes.WORKSHOP, self.c9, [wood])
        
        self.assertTrue(Workshop.objects.filter(building_slot=slot).exists())
        self.assertIsNone(wood.refresh_from_db() or wood.clearing)
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 2)

    def test_build_no_actions_fails(self):
        self.daylight.actions_left = 0
        self.daylight.save()
        wood = CatWoodFactory(player=self.player, clearing=self.c1)
        
        with self.assertRaisesMessage(ValueError, "No actions remaining"):
            cat_build(self.player, CatBuildingTypes.WORKSHOP, self.c9, [wood])

    def test_build_insufficient_wood_fails(self):
        # Workshop level 1 cost is 1. We provide 0.
        with self.assertRaisesMessage(ValueError, "Not enough wood tokens provided"):
            cat_build(self.player, CatBuildingTypes.WORKSHOP, self.c9, [])

    def test_build_connected_thru_rule_success(self):
        # Chain C1 <-> C5 <-> C2. C1 and C2 are NOT adjacent.
        c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        
        # Cats rule C1 (Keep), C5 (Workshop), C2 (Garrison warrior) at game start.
        # Verify rulership
        self.assertEqual(determine_clearing_rule(self.c1), self.player)
        self.assertEqual(determine_clearing_rule(self.c5), self.player)
        self.assertEqual(determine_clearing_rule(c2), self.player)
        
        # Wood in C1
        wood = CatWoodFactory(player=self.player, clearing=self.c1)
        
        # Build Sawmill in C2 (We already have 1 Sawmill in C1, so cost is 1)
        cat_build(self.player, CatBuildingTypes.SAWMILL, c2, [wood])
        
        from game.models.cats.buildings import Sawmill
        self.assertTrue(Sawmill.objects.filter(building_slot__clearing=c2).exists())

    def test_build_chain_broken_by_rule_fails(self):
        # target: build in c2
        c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        # Need to isolate C1 from C2 by removing rule from c5, c6, c10
        c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        c6 = Clearing.objects.get(game=self.game, clearing_number=6)
        c10 = Clearing.objects.get(game=self.game, clearing_number=10)
        
        # Insert a chunk of birds at C5, C6, AND C10 to block all paths from C1
        WarriorFactory.create_batch(3, player=self.birds_player, clearing=c5)
        WarriorFactory.create_batch(3, player=self.birds_player, clearing=c6)
        WarriorFactory.create_batch(3, player=self.birds_player, clearing=c10)
        
        # Verify Birds rule C5, C6, and C10
        self.assertEqual(determine_clearing_rule(c5), self.birds_player)
        self.assertEqual(determine_clearing_rule(c6), self.birds_player)
        self.assertEqual(determine_clearing_rule(c10), self.birds_player)
        
        # Wood in C1
        wood = CatWoodFactory(player=self.player, clearing=self.c1)
        
        # Build Sawmill in C2 -> Should fail because no ruled path exists
        with self.assertRaisesMessage(ValueError, "Not enough connected wood to build"):
            cat_build(self.player, CatBuildingTypes.SAWMILL, c2, [wood])

class CatOverworkTests(CatBaseTestCase):
    def test_overwork_success(self):
        card_enum = CardsEP.AMBUSH_RED
        card_obj = CardFactory(game=self.game, card_type=card_enum.name)
        HandEntry.objects.create(player=self.player, card=card_obj)
        
        initial_wood = CatWood.objects.filter(player=self.player, clearing=self.c1).count()
        overwork(self.player, self.c1, card_enum)
        
        self.assertEqual(CatWood.objects.filter(player=self.player, clearing=self.c1).count(), initial_wood + 1)
        self.assertFalse(HandEntry.objects.filter(player=self.player, card=card_obj).exists())
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 2)

    def test_overwork_no_actions_fails(self):
        self.daylight.actions_left = 0
        self.daylight.save()
        card_enum = CardsEP.AMBUSH_RED
        card_obj = CardFactory(game=self.game, card_type=card_enum.name)
        HandEntry.objects.create(player=self.player, card=card_obj)
        
        with self.assertRaisesMessage(ValueError, "No actions remaining"):
            overwork(self.player, self.c1, card_enum)

    def test_overwork_wrong_suit_fails(self):
        # C1 is Fox. Provide Mouse card.
        card_enum = CardsEP.AMBUSH_ORANGE
        card_obj = CardFactory(game=self.game, card_type=card_enum.name)
        HandEntry.objects.create(player=self.player, card=card_obj)
        
        with self.assertRaisesMessage(ValueError, "No sawmill in that clearing"):
            overwork(self.player, self.c1, card_enum)

    def test_overwork_bird_suit_succeeds(self):
        # Bird card should work for ANY clearing with a sawmill.
        card_enum = CardsEP.AMBUSH_WILD
        card_obj = CardFactory(game=self.game, card_type=card_enum.name)
        HandEntry.objects.create(player=self.player, card=card_obj)
        
        initial_wood = CatWood.objects.filter(player=self.player, clearing=self.c1).count()
        overwork(self.player, self.c1, card_enum)
        
        self.assertEqual(CatWood.objects.filter(player=self.player, clearing=self.c1).count(), initial_wood + 1)
        self.assertFalse(HandEntry.objects.filter(player=self.player, card=card_obj).exists())

class CatMovementTests(CatBaseTestCase):
    def test_march_uses_one_action_for_two_moves(self):
        # 1st move (C1 to C5)
        cat_march(self.player, self.c1, self.c5, 1)
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 2)
        self.assertTrue(self.daylight.midmarch)
        
        # 2nd move (C5 back to C1)
        cat_march(self.player, self.c5, self.c1, 1)
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 2)
        self.assertFalse(self.daylight.midmarch)
        
        # 3rd move (C1 to C9)
        cat_march(self.player, self.c1, self.c9, 1)
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 1)
        self.assertTrue(self.daylight.midmarch)

class CatActionTests(CatBaseTestCase):
    def test_birds_for_hire_adds_actions(self):
        card_enum = CardsEP.AMBUSH_WILD
        card_obj = CardFactory(game=self.game, card_type=card_enum.name)
        HandEntry.objects.create(player=self.player, card=card_obj)
        
        initial_actions = self.daylight.actions_left
        birds_for_hire(self.player, card_enum)
        
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, initial_actions + 1)
        self.assertFalse(HandEntry.objects.filter(player=self.player, card=card_obj).exists())

    def test_birds_for_hire_non_bird_fails(self):
        card_enum = CardsEP.AMBUSH_RED
        card_obj = CardFactory(game=self.game, card_type=card_enum.name)
        HandEntry.objects.create(player=self.player, card=card_obj)
        
        with self.assertRaisesMessage(ValueError, "Not a bird card"):
            birds_for_hire(self.player, card_enum)

    def test_end_actions_step(self):
        end_action_step(self.player)
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, CatDaylight.CatDaylightSteps.COMPLETED)

class CatCraftingTests(CatBaseTestCase):
    def setUp(self):
        super().setUp()
        # Set phase to Daylight CRAFTING
        self.daylight.step = CatDaylight.CatDaylightSteps.CRAFTING
        self.daylight.save()

    def test_crafting_rabbit_partisans_success(self):
        # Rabbit Partisans: requires 1 Rabbit (Yellow)
        # C5 is Rabbit (self.c5) and already has 1 workshop from setup.
        workshop1 = Workshop.objects.get(building_slot__clearing=self.c5)
        
        card_enum = CardsEP.RABBIT_PARTISANS
        card_obj = CardFactory(game=self.game, card_type=card_enum.name)
        HandEntry.objects.create(player=self.player, card=card_obj)
        
        # Craft it (Rabbit Partisans requires 1 Rabbit)
        cat_craft_card(self.player, card_enum, [workshop1])
        
        # Verify card is crafted
        from game.models.game_models import CraftedCardEntry
        self.assertTrue(CraftedCardEntry.objects.filter(player=self.player, card__card_type=card_enum.name).exists())



