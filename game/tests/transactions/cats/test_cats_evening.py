from django.test import TestCase
from game.models.game_models import Faction, HandEntry
from game.models.cats.buildings import Recruiter
from game.models.cats.turn import CatBirdsong, CatDaylight, CatEvening
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory
from game.transactions.cats import cat_evening_draw, check_auto_discard, cat_discard_card
from game.game_data.cards.exiles_and_partisans import CardsEP

class CatEveningBaseTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.player = self.game.players.get(faction=Faction.CATS)
        
        self.turn = CatEvening.objects.get(turn__player=self.player).turn
        
        # Mark previous phases as COMPLETED so get_phase returns evening
        birdsong = self.turn.birdsong
        birdsong.step = CatBirdsong.CatBirdsongSteps.COMPLETED
        birdsong.save()
        
        daylight = self.turn.daylight
        daylight.step = CatDaylight.CatDaylightSteps.COMPLETED
        daylight.save()
        
        self.evening = self.turn.evening
        self.evening.step = CatEvening.CatEveningSteps.DRAWING
        self.evening.save()

class CatEveningFlowTests(CatEveningBaseTestCase):
    def test_draw_cards_success(self):
        initial_hand_count = HandEntry.objects.filter(player=self.player).count()
        cat_evening_draw(self.player)
        
        # With 1 recruiter, bonus is 0. Total draw 1.
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), initial_hand_count + 1)
        
        # Check step advancement. It goes DRAWING -> DISCARDING -> check_auto_discard -> COMPLETED
        # because hand size is small.
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, CatEvening.CatEveningSteps.COMPLETED)


    def test_auto_discard_success(self):
        # Set step to DISCARDING
        self.evening.step = CatEvening.CatEveningSteps.DISCARDING
        self.evening.save()
        
        # Hand size <= 5.
        HandEntry.objects.filter(player=self.player).delete()
        for _ in range(3):
            HandEntry.objects.create(player=self.player, card=CardFactory(game=self.game))
            
        check_auto_discard(self.player)
        
        # Should transition to COMPLETED
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, CatEvening.CatEveningSteps.COMPLETED)

    def test_manual_discard_required(self):
        # Hand size > 5. Let's ensure hand is 6.
        HandEntry.objects.filter(player=self.player).delete()
        cards = []
        for _ in range(6):
            c = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
            HandEntry.objects.create(player=self.player, card=c)
            cards.append(c)
            
        self.evening.step = CatEvening.CatEveningSteps.DISCARDING
        self.evening.save()
        
        check_auto_discard(self.player)
        
        # Should NOT transition to COMPLETED. 
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, CatEvening.CatEveningSteps.DISCARDING)
        
        # Now discard one card manually
        cat_discard_card(self.player, CardsEP.AMBUSH_RED)
        
        # Now it should be COMPLETED
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, CatEvening.CatEveningSteps.COMPLETED)
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), 5)

