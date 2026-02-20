import logging
from django.test import TestCase
from game.models import (
    Faction,
    Game,
    Player,
    Clearing,
    HandEntry,
    Card,
    Warrior,
    Building,
    Token,
    Suit,
    DiscardPileEntry
)
from game.models.wa.buildings import WABase
from game.models.wa.player import SupporterStackEntry, OfficerEntry
from game.models.wa.tokens import WASympathy
from game.models.wa.turn import WATurn, WAEvening, WADaylight, WABirdsong
from game.tests.my_factories import (
    GameSetupWithFactionsFactory,
    CardFactory,
    WarriorFactory,
    HandEntryFactory
)
from game.transactions.wa import (
    operation_recruit,
    operation_organize,
    end_evening_operations,
    draw_cards,
    check_discard_step,
    end_turn
)
from game.queries.wa.turn import get_phase
from game.queries.general import get_player_hand_size

logger = logging.getLogger(__name__)

class WAEveningBaseTestCase(TestCase):
    def setUp(self):
        # Create a game with Cats and WA
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.WOODLAND_ALLIANCE])
        self.player = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Ensure WA's turn
        self.player.turn_order = 1
        self.player.save()
        self.game.current_turn = 1
        self.game.save()
        
        # Get turn and phases
        self.turn = WATurn.objects.get(player=self.player, turn_number=0)
        
        # Complete Birdsong and Daylight to get to Evening
        self.birdsong = self.turn.birdsong.first()
        self.birdsong.step = WABirdsong.WABirdsongSteps.COMPLETED
        self.birdsong.save()
        
        self.daylight = self.turn.daylight.first()
        self.daylight.step = WADaylight.WADaylightSteps.COMPLETED
        self.daylight.save()
        
        self.evening = self.turn.evening.first()
        self.evening.step = WAEvening.WAEveningSteps.MILITARY_OPERATIONS
        self.evening.save()
        
        # Clearings by suit, avoiding the Keep (usually in clearing 1)
        available_clearings = Clearing.objects.filter(game=self.game)
        # Exclude clearings that have a token (the Keep is a token)
        available_clearings = available_clearings.exclude(token__isnull=False)
        
        self.fox_clearing = available_clearings.filter(suit=Suit.RED).first()
        self.mouse_clearing = available_clearings.filter(suit=Suit.ORANGE).first()
        self.rabbit_clearing = available_clearings.filter(suit=Suit.YELLOW).first()

    def add_officer(self):
        warrior = Warrior.objects.filter(player=self.player, clearing=None).first()
        if not warrior:
            warrior = WarriorFactory(player=self.player, clearing=None)
        return OfficerEntry.objects.create(player=self.player, warrior=warrior)

    def add_base(self, clearing):
        from game.queries.general import available_building_slot
        from game.models import BuildingSlot
        if not BuildingSlot.objects.filter(clearing=clearing).exists():
            BuildingSlot.objects.create(clearing=clearing, building_slot_number=0)
            
        base = WABase.objects.get(player=self.player, suit=clearing.suit)
        slot = available_building_slot(clearing)
        if not slot:
            slot = BuildingSlot.objects.filter(clearing=clearing).first()
            Building.objects.filter(building_slot=slot).delete()
        base.building_slot = slot
        base.save()
        return base

    def add_sympathy(self, clearing):
        token = WASympathy.objects.filter(player=self.player, clearing=None).first()
        token.clearing = clearing
        token.save()
        return token

class WAEveningOperationsTests(WAEveningBaseTestCase):
    def test_recruit_success(self):
        self.add_base(self.fox_clearing)
        self.add_officer()
        
        initial_warriors = Warrior.objects.filter(player=self.player, clearing=self.fox_clearing).count()
        operation_recruit(self.player, self.fox_clearing)
        
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=self.fox_clearing).count(), initial_warriors + 1)
        # Check officer used
        self.assertTrue(OfficerEntry.objects.get(player=self.player).used)

    def test_recruit_fail_no_base(self):
        self.add_officer()
        with self.assertRaisesRegex(ValueError, "No base in that clearing"):
            operation_recruit(self.player, self.fox_clearing)

    def test_organize_success(self):
        self.add_officer()
        WarriorFactory(player=self.player, clearing=self.fox_clearing)
        # Place initial sympathy in a DIFFERENT clearing, because the first one placed does not score points
        self.add_sympathy(self.mouse_clearing)
        
        initial_vp = self.player.score
        operation_organize(self.player, self.fox_clearing)
        
        # Warrior should be removed
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=self.fox_clearing).count(), 0)
        # Sympathy should be placed
        self.assertTrue(WASympathy.objects.filter(player=self.player, clearing=self.fox_clearing).exists())
        # Score should increase
        self.assertGreater(self.player.score, initial_vp)
        # Officer used
        self.assertTrue(OfficerEntry.objects.get(player=self.player).used)

    def test_organize_fail_no_warrior(self):
        self.add_officer()
        # No warrior in clearing
        with self.assertRaisesRegex(ValueError, "No warrior in that clearing"):
            operation_organize(self.player, self.fox_clearing)

    def test_organize_fail_already_sympathetic(self):
        self.add_officer()
        WarriorFactory(player=self.player, clearing=self.fox_clearing)
        self.add_sympathy(self.fox_clearing)
        
        with self.assertRaisesRegex(ValueError, "Player already has a sympathy token in this clearing"):
            operation_organize(self.player, self.fox_clearing)

    def test_operation_fail_no_officers(self):
        # No officers added
        with self.assertRaisesRegex(ValueError, "No unused officers"):
            operation_recruit(self.player, self.fox_clearing)

    def test_operation_fail_all_officers_used(self):
        officer = self.add_officer()
        officer.used = True
        officer.save()
        
        with self.assertRaisesRegex(ValueError, "No unused officers"):
            operation_recruit(self.player, self.fox_clearing)

class WAEveningTransitionTests(WAEveningBaseTestCase):
    def test_end_operations_advances_to_drawing(self):
        end_evening_operations(self.player)
        self.evening.refresh_from_db()
        # goes to end of evening unless there are cards to discard
        self.assertEqual(self.evening.step, WAEvening.WAEveningSteps.COMPLETED.value)

    def test_draw_cards_count_with_bases(self):
        # 1 basic + 1 for each base
        self.add_base(self.fox_clearing)
        self.add_base(self.mouse_clearing)
        
        self.evening.step = WAEvening.WAEveningSteps.DRAWING
        self.evening.save()
        
        initial_hand = get_player_hand_size(self.player)
        draw_cards(self.player)
        
        # Should draw 1 + 2 = 3 cards
        self.assertEqual(get_player_hand_size(self.player), initial_hand + 3)
        
        # Should auto-advance to DISCARDING if hand size <= 5
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, WAEvening.WAEveningSteps.DISCARDING)

    def test_check_discard_auto_advances_if_limit_met(self):
        self.evening.step = WAEvening.WAEveningSteps.DISCARDING
        self.evening.save()
        
        # Ensure hand size <= 5
        HandEntry.objects.filter(player=self.player).delete()
        for _ in range(5):
            HandEntryFactory(player=self.player)
            
        check_discard_step(self.player)
        
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, WAEvening.WAEveningSteps.COMPLETED)

    def test_check_discard_pauses_if_over_limit(self):
        self.evening.step = WAEvening.WAEveningSteps.DISCARDING
        self.evening.save()
        
        # Ensure hand size > 5
        HandEntry.objects.filter(player=self.player).delete()
        for _ in range(6):
            HandEntryFactory(player=self.player)
            
        check_discard_step(self.player)
        
        # Should NOT advance
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, WAEvening.WAEveningSteps.DISCARDING)

    def test_end_turn_resets_components(self):
        self.evening.step = WAEvening.WAEveningSteps.COMPLETED
        self.evening.save()
        
        # Add a "used" officer
        officer = self.add_officer()
        officer.used = True
        officer.save()
        
        # Add a "crafted_with" sympathy
        sympathy = self.add_sympathy(self.mouse_clearing)
        sympathy.crafted_with = True
        sympathy.save()
        
        end_turn(self.player)
        
        # Officer should be unused
        officer.refresh_from_db()
        self.assertFalse(officer.used)
        
        # Sympathy should be reset
        sympathy.refresh_from_db()
        self.assertFalse(sympathy.crafted_with)
        
        # Next turn should be created
        self.assertTrue(WATurn.objects.filter(player=self.player, turn_number=1).exists())
