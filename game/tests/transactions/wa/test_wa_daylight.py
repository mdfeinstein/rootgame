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
from game.models.wa.turn import WATurn, WADaylight, WABirdsong
from game.tests.my_factories import (
    GameSetupWithFactionsFactory,
    CardFactory,
    WarriorFactory,
    HandEntryFactory
)
from game.transactions.wa import (
    wa_craft_card,
    mobilize_supporter,
    training,
    end_daylight_actions,
)
from game.game_data.cards.exiles_and_partisans import CardsEP

logger = logging.getLogger(__name__)

class WADaylightBaseTestCase(TestCase):
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
        
        # Complete Birdsong to get to Daylight
        self.birdsong = self.turn.birdsong.first()
        self.birdsong.step = WABirdsong.WABirdsongSteps.COMPLETED
        self.birdsong.save()
        
        self.daylight = self.turn.daylight.first()
        self.daylight.step = WADaylight.WADaylightSteps.ACTIONS
        self.daylight.save()
        
        # Clear default supporters added by factory setup
        SupporterStackEntry.objects.filter(player=self.player).delete()
        
        # Clearings by suit for easy access
        self.fox_clearing = Clearing.objects.filter(game=self.game, suit=Suit.RED).first()
        self.mouse_clearing = Clearing.objects.filter(game=self.game, suit=Suit.ORANGE).first()
        self.rabbit_clearing = Clearing.objects.filter(game=self.game, suit=Suit.YELLOW).first()

    def add_card_to_hand(self, card_enum):
        card = Card.objects.filter(game=self.game, card_type=card_enum.name).first()
        if not card:
            card = CardFactory(game=self.game, card_type=card_enum.name)
        return HandEntry.objects.create(player=self.player, card=card)

    def add_sympathy(self, clearing):
        """Places a sympathy token in a clearing"""
        token = WASympathy.objects.filter(player=self.player, clearing=None).first()
        token.clearing = clearing
        token.save()
        return token

    def add_base(self, clearing):
        """Places a base in a clearing"""
        from game.queries.general import available_building_slot
        from game.models import BuildingSlot
        # Ensure clearing has slots
        if not BuildingSlot.objects.filter(clearing=clearing).exists():
            BuildingSlot.objects.create(clearing=clearing, building_slot_number=0)

        base = WABase.objects.get(player=self.player, suit=clearing.suit)
        slot = available_building_slot(clearing)
        if not slot:
            slot = BuildingSlot.objects.filter(clearing=clearing).first()
            # Clear existing building if any
            from game.models import Building
            Building.objects.filter(building_slot=slot).delete()
        
        base.building_slot = slot
        base.save()
        base.refresh_from_db()
        return base

class WADaylightTests(WADaylightBaseTestCase):
    def test_sympathy_crafting_success(self):
        # 1. Setup: Sympathy in Mouse clearing, Crafting 'Mouse Partisans' (needs 1 orange)
        self.add_sympathy(self.mouse_clearing)
        card_enum = CardsEP.MOUSE_PARTISANS
        self.add_card_to_hand(card_enum)
        
        sympathy = WASympathy.objects.get(player=self.player, clearing=self.mouse_clearing)
        
        # 2. Craft
        wa_craft_card(self.player, card_enum, [sympathy])
        
        # Check card crafted
        from game.models import CraftedCardEntry
        self.assertTrue(CraftedCardEntry.objects.filter(player=self.player, card__card_type=card_enum.name).exists())
        self.assertFalse(HandEntry.objects.filter(player=self.player, card__card_type=card_enum.name).exists())
        # Check sympathy marked as crafted_with
        sympathy.refresh_from_db()
        self.assertTrue(sympathy.crafted_with)

    def test_mobilize_success(self):
        card_enum = CardsEP.AMBUSH_RED
        self.add_card_to_hand(card_enum)
        
        initial_supporters = SupporterStackEntry.objects.filter(player=self.player).count()
        
        mobilize_supporter(self.player, card_enum)
        
        self.assertEqual(SupporterStackEntry.objects.filter(player=self.player).count(), initial_supporters + 1)
        self.assertFalse(HandEntry.objects.filter(player=self.player, card__card_type=card_enum.name).exists())

    def test_mobilize_fail_card_not_in_hand(self):
        card_enum = CardsEP.AMBUSH_RED
        # Don't add to hand
        
        with self.assertRaisesRegex(ValueError, "Player does not have card"):
            mobilize_supporter(self.player, card_enum)

    def test_training_success_fox(self):
        # 1. Setup: Fox base on board, Fox card in hand, warriors in supply
        self.add_base(self.fox_clearing)
        card_enum = CardsEP.AMBUSH_RED
        self.add_card_to_hand(card_enum)
        
        initial_officers = OfficerEntry.objects.filter(player=self.player).count()
        
        # 2. Train
        training(self.player, card_enum)
        
        # Check officer added
        self.assertEqual(OfficerEntry.objects.filter(player=self.player).count(), initial_officers + 1)
        # Check card discarded
        self.assertFalse(HandEntry.objects.filter(player=self.player, card__card_type=card_enum.name).exists())
        self.assertTrue(DiscardPileEntry.objects.filter(game=self.game, card__card_type=card_enum.name).exists())

    def test_training_success_bird_wild(self):
        # Training with a Bird card should work even if only a Mouse base is on board
        self.add_base(self.mouse_clearing)
        card_enum = CardsEP.AMBUSH_WILD
        self.add_card_to_hand(card_enum)
        
        training(self.player, card_enum)
        self.assertEqual(OfficerEntry.objects.filter(player=self.player).count(), 1)

    def test_training_fail_card_not_in_hand(self):
        self.add_base(self.fox_clearing)
        card_enum = CardsEP.AMBUSH_RED
        
        with self.assertRaisesRegex(ValueError, "Player does not have card"):
            training(self.player, card_enum)

    def test_training_fail_no_base(self):
        # Fox card, but no Fox base (only Rabbit base)
        self.add_base(self.rabbit_clearing)
        card_enum = CardsEP.AMBUSH_RED
        self.add_card_to_hand(card_enum)
        
        with self.assertRaisesRegex(ValueError, "Suit does not match a base on the board"):
            training(self.player, card_enum)

    def test_training_fail_no_reserve(self):
        self.add_base(self.fox_clearing)
        card_enum = CardsEP.AMBUSH_RED
        self.add_card_to_hand(card_enum)
        
        # Empty the reserve
        Warrior.objects.filter(player=self.player, clearing=None).delete()
        
        with self.assertRaisesRegex(ValueError, "No warriors in reserve"):
            training(self.player, card_enum)

    def test_end_daylight_advances_to_evening(self):
        end_daylight_actions(self.player)
        
        from game.queries.wa.turn import get_phase
        from game.models.wa.turn import WAEvening
        phase = get_phase(self.player)
        self.assertIsInstance(phase, WAEvening)
        self.assertEqual(phase.step, WAEvening.WAEveningSteps.MILITARY_OPERATIONS)
