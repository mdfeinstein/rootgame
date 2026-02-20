import logging
from django.test import TestCase
from game.models import (
    Faction,
    Game,
    Player,
    Clearing,
    HandEntry,
    BirdTurn,
    BirdBirdsong,
    BirdDaylight,
    BirdEvening,
    BirdRoost,
    Suit,
    Warrior,
)
from game.models.birds.player import BirdLeader, DecreeEntry, Vizier
from game.tests.my_factories import (
    GameFactory,
    PlayerFactory,
    CardFactory,
    HandEntryFactory,
    GameSetupWithFactionsFactory,
)
from game.transactions.birds import (
    roost_scoring,
    draw_cards,
    check_discard_step,
    discard_card,
    begin_evening,
)
from game.game_data.cards.exiles_and_partisans import CardsEP

logger = logging.getLogger(__name__)

class BirdEveningBaseTestCase(TestCase):
    def setUp(self):
        # Create a game with Cats and Birds
        self.game = GameSetupWithFactionsFactory()
        self.player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Set current turn to Birds
        self.game.current_turn = self.player.turn_order
        self.game.save()
        
        # Create a turn for Birds
        self.turn = BirdTurn.create_turn(self.player)
        
        # Complete Birdsong and Daylight
        self.birdsong = self.turn.birdsong.first()
        self.birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        self.birdsong.save()
        
        self.daylight = self.turn.daylight.first()
        self.daylight.step = BirdDaylight.BirdDaylightSteps.COMPLETED
        self.daylight.save()
        
        self.evening = self.turn.evening.first()
        self.evening.step = BirdEvening.BirdEveningSteps.SCORING
        self.evening.save()

        # Birds start with 1 roost in clearing 3
        self.roost3 = BirdRoost.objects.get(player=self.player, building_slot__clearing__clearing_number=3)

    def add_roosts(self, count):
        """Adds more roosts to the player up to the count (including the starting one)"""
        current_roosts = BirdRoost.objects.filter(player=self.player, building_slot__isnull=False).count()
        if current_roosts >= count:
            return
        
        # Find clearings without roosts
        clearings = Clearing.objects.filter(game=self.game, buildingslot__building__isnull=True).distinct()

        for i in range(count - current_roosts):
            clearing = clearings[i]
            from game.queries.general import available_building_slot
            slot = available_building_slot(clearing)
            roost = BirdRoost.objects.filter(player=self.player, building_slot__isnull=True).first()
            roost.building_slot = slot
            roost.save()

    def reset_phase_and_turn(self, step=BirdEvening.BirdEveningSteps.SCORING):
        self.player.refresh_from_db()
        self.game.current_turn = self.player.turn_order
        self.game.save()
        
        # Get the LATEST turn for the player
        turn = BirdTurn.objects.filter(player=self.player).order_by("-turn_number").first()
        
        # Ensure older phases are completed so get_phase gets to Evening
        BirdBirdsong.objects.filter(turn=turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=turn).update(step=BirdDaylight.BirdDaylightSteps.COMPLETED)
        
        # Set the target step
        BirdEvening.objects.filter(turn=turn).update(step=step)
        
        # Ensure evening reference is updated? No, get_phase will fetch it.
        # But we might need to refresh local evening reference if used for assertions.
        self.evening = BirdEvening.objects.get(turn=turn)

class BirdEveningScoringAndDrawTests(BirdEveningBaseTestCase):
    def test_scoring_different_roost_counts(self):
        # 1 roost = 0 VP
        roost_scoring(self.player)
        self.player.refresh_from_db()
        self.assertEqual(self.player.score, 0)
        
        # Reset for next check
        self.reset_phase_and_turn(BirdEvening.BirdEveningSteps.SCORING)
        
        # 2 roosts = 1 VP
        self.add_roosts(2)
        roost_scoring(self.player)
        self.player.refresh_from_db()
        self.assertEqual(self.player.score, 1)
        
        # Reset
        self.reset_phase_and_turn(BirdEvening.BirdEveningSteps.SCORING)
        
        # 3 roosts = 2 VP
        self.add_roosts(3)
        roost_scoring(self.player)
        self.player.refresh_from_db()
        self.assertEqual(self.player.score, 1 + 2) # Cumulative

        # 7 roosts = 5 VP
        self.add_roosts(7)
        self.reset_phase_and_turn(BirdEvening.BirdEveningSteps.SCORING)
        roost_scoring(self.player)
        self.player.refresh_from_db()
        self.assertEqual(self.player.score, 1 + 2 + 5)

    def test_draw_cards_count(self):
        self.reset_phase_and_turn(BirdEvening.BirdEveningSteps.DRAWING)
        # 1 roost = 1 card
        initial_hand = HandEntry.objects.filter(player=self.player).count()
        draw_cards(self.player)
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), initial_hand + 1)
        
        # Reset to DRAWING step
        self.reset_phase_and_turn(BirdEvening.BirdEveningSteps.DRAWING)
        
        # 3 roosts = 2 cards
        self.add_roosts(3)
        draw_cards(self.player)
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), initial_hand + 1 + 2)
        
        # 6 roosts = 3 cards
        self.reset_phase_and_turn(BirdEvening.BirdEveningSteps.DRAWING)
        self.add_roosts(6)
        draw_cards(self.player)
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), initial_hand + 1 + 2 + 3)


class BirdEveningDiscardTests(BirdEveningBaseTestCase):
    def test_auto_advance_if_hand_small(self):
        # Set hand size to 4
        HandEntry.objects.filter(player=self.player).delete()
        for _ in range(4):
            HandEntry.objects.create(player=self.player, card=CardFactory(game=self.game))
            
        self.evening.step = BirdEvening.BirdEveningSteps.DISCARDING
        self.evening.save()
        
        check_discard_step(self.player)
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, BirdEvening.BirdEveningSteps.COMPLETED)

    def test_manual_discard_logic(self):
        # Set hand size to 7
        HandEntry.objects.filter(player=self.player).delete()
        cards = []
        for _ in range(7):
            c = CardFactory(game=self.game)
            cards.append(c)
            HandEntry.objects.create(player=self.player, card=c)
            
        self.evening.step = BirdEvening.BirdEveningSteps.DISCARDING
        self.evening.save()
        
        # check_discard_step should NOT advance to COMPLETED
        check_discard_step(self.player)
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, BirdEvening.BirdEveningSteps.DISCARDING)
        
        # Discard one card (still 6)
        discard_card(self.player, CardsEP[cards[0].card_type])
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, BirdEvening.BirdEveningSteps.DISCARDING)
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), 6)
        
        # Discard another card (now 5) -> should auto-advance
        discard_card(self.player, CardsEP[cards[1].card_type])
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, BirdEvening.BirdEveningSteps.COMPLETED)
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), 5)

    def test_discard_error_if_not_needed(self):
        # Hand size 5
        HandEntry.objects.filter(player=self.player).delete()
        cards = []
        for _ in range(5):
            c = CardFactory(game=self.game)
            cards.append(c)
            HandEntry.objects.create(player=self.player, card=c)
            
        self.evening.step = BirdEvening.BirdEveningSteps.DISCARDING
        self.evening.save()
        
        with self.assertRaisesRegex(ValueError, "Player must have more than 5 cards to discard"):
            discard_card(self.player, CardsEP[cards[0].card_type])

class BirdEveningFullAutomationTests(BirdEveningBaseTestCase):
    def test_begin_evening_auto_completes(self):
        # Starting hand is small (usually 3ish from factory)
        # 1 roost => scores 0, draws 1 => total hand size reflects that
        initial_hand = HandEntry.objects.filter(player=self.player).count()
        begin_evening(self.player)
        
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, BirdEvening.BirdEveningSteps.COMPLETED)
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), initial_hand + 1)
        self.assertEqual(self.player.score, 0)

    def test_begin_evening_pauses_on_discard(self):
        # Give player many cards
        for _ in range(5):
            HandEntry.objects.create(player=self.player, card=CardFactory(game=self.game))
            
        # 1 roost => scores 0, draws 1 => hand size will be > 5
        begin_evening(self.player)
        
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, BirdEvening.BirdEveningSteps.DISCARDING)
