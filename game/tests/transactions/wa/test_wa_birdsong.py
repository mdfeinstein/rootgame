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
)
from game.models.wa.buildings import WABase
from game.models.wa.player import SupporterStackEntry, OfficerEntry
from game.models.wa.tokens import WASympathy
from game.models.wa.turn import WATurn, WABirdsong
from game.tests.my_factories import (
    GameSetupWithFactionsFactory,
    CardFactory,
    WarriorFactory,
)
from game.transactions.wa import (
    revolt,
    spread_sympathy,
    end_revolt_step,
    end_spread_sympathy_step,
)
from game.game_data.cards.exiles_and_partisans import CardsEP

logger = logging.getLogger(__name__)

class WABirdsongBaseTestCase(TestCase):
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
        self.birdsong = self.turn.birdsong.first()
        self.birdsong.step = WABirdsong.WABirdsongSteps.REVOLT
        self.birdsong.save()
        
        # Clear default supporters added by factory setup to have a clean slate
        SupporterStackEntry.objects.filter(player=self.player).delete()
        
        # Clearings by suit for easy access
        self.fox_clearing = Clearing.objects.filter(game=self.game, suit=Suit.RED).first()
        self.mouse_clearing = Clearing.objects.filter(game=self.game, suit=Suit.ORANGE).first()
        self.rabbit_clearing = Clearing.objects.filter(game=self.game, suit=Suit.YELLOW).first()

    def add_supporters(self, suit, count):
        """Adds supporters of a specific suit"""
        for _ in range(count):
            # Create a NEW card or find an unused one in deck
            from game.models import DeckEntry
            deck_entry = DeckEntry.objects.filter(game=self.game, card__suit=suit).first()
            if deck_entry:
                card = deck_entry.card
                deck_entry.delete()
            else:
                card = CardFactory(game=self.game, suit=suit)
            SupporterStackEntry.objects.create(player=self.player, card=card)

    def add_sympathy(self, clearing):
        """Places a sympathy token in a clearing"""
        token = WASympathy.objects.filter(player=self.player, clearing=None).first()
        token.clearing = clearing
        token.save()

class WARevoltTests(WABirdsongBaseTestCase):
    def test_revolt_success(self):
        # 1. Setup: Sympathy in Mouse clearing, 2 Mouse supporters
        self.add_sympathy(self.mouse_clearing)
        self.add_supporters(Suit.ORANGE, 2)
        
        # Add enemy pieces to remove (1 warrior, 1 building)
        WarriorFactory(player=self.cats_player, clearing=self.mouse_clearing)
        from game.queries.general import available_building_slot
        from game.models.cats.buildings import Workshop
        slot = available_building_slot(self.mouse_clearing)
        workshop = Workshop.objects.create(player=self.cats_player, building_slot=slot)
        
        initial_score = self.player.score
        
        # 2. Revolt
        revolt(self.player, self.mouse_clearing)
        
        self.player.refresh_from_db()
        # Base placed
        self.assertTrue(WABase.objects.filter(player=self.player, suit=Suit.ORANGE, building_slot__clearing=self.mouse_clearing).exists())
        # Enemy pieces removed from board (not necessarily deleted if they return to supply)
        self.assertFalse(Warrior.objects.filter(player=self.cats_player, clearing=self.mouse_clearing).exists())
        workshop.refresh_from_db()
        self.assertIsNone(workshop.building_slot)
        # Points scored (1 VP for the workshop)
        self.assertEqual(self.player.score, initial_score + 1)
        # Warriors placed (1 for the Mouse sympathy at mouse_clearing)
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=self.mouse_clearing).count(), 1)
        # Officer gained
        self.assertEqual(OfficerEntry.objects.filter(player=self.player).count(), 1)
        # Supporters discarded
        self.assertEqual(SupporterStackEntry.objects.filter(player=self.player).count(), 0)

    def test_revolt_with_bird_supporters(self):
        # Revolt using 1 Mouse and 1 Bird supporter in Mouse clearing
        self.add_sympathy(self.mouse_clearing)
        self.add_supporters(Suit.ORANGE, 1)
        self.add_supporters(Suit.WILD, 1)
        
        revolt(self.player, self.mouse_clearing)
        
        self.assertTrue(WABase.objects.filter(player=self.player, suit=Suit.ORANGE).exists())
        self.assertEqual(SupporterStackEntry.objects.filter(player=self.player).count(), 0)

    def test_revolt_fails_no_sympathy(self):
        self.add_supporters(Suit.ORANGE, 2)
        with self.assertRaisesRegex(ValueError, "No sympathy in that clearing"):
            revolt(self.player, self.mouse_clearing)

    def test_revolt_fails_insufficient_supporters(self):
        self.add_sympathy(self.mouse_clearing)
        self.add_supporters(Suit.ORANGE, 1)
        with self.assertRaisesRegex(ValueError, "Not enough supporters"):
            revolt(self.player, self.mouse_clearing)

    def test_revolt_fails_base_already_on_board(self):
        self.add_sympathy(self.mouse_clearing)
        self.add_supporters(Suit.ORANGE, 2)
        
        # Place Mouse base elsewhere
        from game.queries.general import available_building_slot
        other_mouse = Clearing.objects.filter(game=self.game, suit=Suit.ORANGE).exclude(id=self.mouse_clearing.id).first()
        base = WABase.objects.get(player=self.player, suit=Suit.ORANGE)
        base.building_slot = available_building_slot(other_mouse)
        base.save()
        
        with self.assertRaisesRegex(ValueError, "Matching base is on the board"):
            revolt(self.player, self.mouse_clearing)

class WASpreadSympathyTests(WABirdsongBaseTestCase):
    def test_spread_sympathy_initial(self):
        self.birdsong.step = WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY
        self.birdsong.save()
        
        # 0 sympathy on board, cost 1
        self.add_supporters(Suit.ORANGE, 1)
        spread_sympathy(self.player, self.mouse_clearing)
        
        self.assertTrue(WASympathy.objects.filter(player=self.player, clearing=self.mouse_clearing).exists())
        self.player.refresh_from_db()
        self.assertEqual(self.player.score, 0) # 1st sympathy = 0 VP

    def test_spread_sympathy_adjacency_required(self):
        self.birdsong.step = WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY
        self.birdsong.save()
        
        # Place 1st sympathy in Fox clearing
        self.add_sympathy(self.fox_clearing)
        
        # 3 is not adjacent to 1 in Autumn map.
        target = Clearing.objects.get(game=self.game, clearing_number=3)
        
        self.add_supporters(target.suit, 1)
        with self.assertRaisesRegex(ValueError, "No adjacent sympathies"):
            spread_sympathy(self.player, target)

    def test_sympathy_cost_scaling(self):
        self.birdsong.step = WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY
        self.birdsong.save()
        
        # Place 3 sympathies (costs 1 each)
        clearings = list(Clearing.objects.filter(game=self.game)[:3])
        for c in clearings:
            self.add_sympathy(c)
            
        # 4th sympathy should cost 2. 
        # Pick a target adjacent to one of the above.
        from game.queries.general import get_adjacent_clearings
        target = None
        for c in clearings:
            adjs = get_adjacent_clearings(self.player, c)
            for adj in adjs:
                if not WASympathy.objects.filter(player=self.player, clearing=adj).exists():
                    target = adj
                    break
            if target: break
            
        self.assertIsNotNone(target)
        self.assertEqual(WASympathy.objects.filter(player=self.player, clearing__isnull=False).count(), 3)
        
        # Cost 2
        self.add_supporters(target.suit, 2)
        spread_sympathy(self.player, target)
        self.assertTrue(WASympathy.objects.filter(player=self.player, clearing=target).exists())

    def test_martial_law(self):
        self.birdsong.step = WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY
        self.birdsong.save()
        
        # 0 sympathy on board, cost 1. Martial law adds +1.
        WarriorFactory.create_batch(3, player=self.cats_player, clearing=self.mouse_clearing)
        
        self.add_supporters(Suit.ORANGE, 1)
        with self.assertRaisesRegex(ValueError, "Not enough supporters"):
            spread_sympathy(self.player, self.mouse_clearing)
            
        self.add_supporters(Suit.ORANGE, 1) # Now 2
        spread_sympathy(self.player, self.mouse_clearing)
        self.assertTrue(WASympathy.objects.filter(player=self.player, clearing=self.mouse_clearing).exists())

    def test_spread_sympathy_fails_already_has_sympathy(self):
        self.birdsong.step = WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY
        self.birdsong.save()
        
        # Place initial sympathy
        self.add_sympathy(self.mouse_clearing)
        
        # Try to spread to same clearing
        self.add_supporters(Suit.ORANGE, 1)
        with self.assertRaisesRegex(ValueError, "Player already has a sympathy token in this clearing"):
            spread_sympathy(self.player, self.mouse_clearing)

    def test_end_revolt_advances_step(self):
        self.birdsong.step = WABirdsong.WABirdsongSteps.REVOLT
        self.birdsong.save()
        
        end_revolt_step(self.player)
        
        self.birdsong.refresh_from_db()
        self.assertEqual(self.birdsong.step, WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY)

    def test_end_spread_sympathy_advances_to_completed(self):
        self.birdsong.step = WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY
        self.birdsong.save()
        
        end_spread_sympathy_step(self.player)
        
        self.birdsong.refresh_from_db()
        self.assertEqual(self.birdsong.step, WABirdsong.WABirdsongSteps.COMPLETED)
        
        # Verify get_phase now returns Daylight
        from game.queries.wa.turn import get_phase
        from game.models.wa.turn import WADaylight
        phase = get_phase(self.player)
        self.assertIsInstance(phase, WADaylight)
