from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, Suit, Piece, HandEntry
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowTurn, CrowDaylight, CrowEvening
from game.tests.my_factories import GameSetupFactory, CardFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.crows.evening import do_exert_action, calculate_crow_draw_amount, check_discard_step, discard_card
from game.transactions.crows.actions import crows_plot
from game.tests.logging_mixin import LoggingTestMixin
from game.models.game_log import LogType

class CrowEveningTestCase(LoggingTestMixin, TestCase):
    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.CATS, Faction.CROWS])
        self.player = self.game.players.get(faction=Faction.CROWS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        from game.models.cats.turn import CatTurn
        CatTurn.create_turn(self.cats_player)
        
        self.game.current_turn = self.player.turn_order
        self.game.save()
        
        self.turn = CrowTurn.create_turn(self.player)
        self.birdsong = self.turn.birdsong.first()
        self.birdsong.step = self.birdsong.CrowBirdsongSteps.COMPLETED
        self.birdsong.save()
        
        self.daylight = self.turn.daylight.first()
        self.daylight.step = CrowDaylight.CrowDaylightSteps.COMPLETED
        self.daylight.save()
        
        self.evening = self.turn.evening.first()
        self.evening.step = CrowEvening.CrowEveningSteps.EXERT
        self.evening.save()

        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        self.c1.connected_clearings.add(self.c2)
        self.c2.connected_clearings.add(self.c1)
        
        c1_ids = list(Warrior.objects.filter(player=self.player).values_list('id', flat=True)[:5])
        Warrior.objects.filter(id__in=c1_ids).update(clearing=self.c1)

    def test_do_exert_action_marks_used(self):
        self.assertFalse(self.evening.exert_used)
        
        do_exert_action(self.player, "move", origin=self.c1, destination=self.c2, count=1)
        
        self.evening.refresh_from_db()
        self.assertTrue(self.evening.exert_used)
        self.assertEqual(self.evening.step, CrowEvening.CrowEveningSteps.COMPLETED)
        
        # Verify Logs (Move)
        self.assertLogExists(LogType.MOVE, player=self.player, origin_clearing_number=self.c1.clearing_number, dest_clearing_number=self.c2.clearing_number, warriors_moved=1)

    def test_exert_fails_if_already_exerted(self):
        self.evening.exert_used = True
        self.evening.save()
        with self.assertRaisesMessage(ValueError, "Exert already used this turn"):
            do_exert_action(self.player, "move", origin=self.c1, destination=self.c2, count=1)

    def test_plot_in_evening_uses_daylight_cost(self):
        # Fake that 2 plots were placed in daylight
        self.daylight.plots_placed = 2
        self.daylight.save()

        # Cost should be 3
        crows_plot(self.player, self.c1, PlotToken.PlotType.BOMB)
        self.assertEqual(Warrior.objects.filter(clearing=self.c1, player=self.player).count(), 2) # Started with 5
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.plots_placed, 3)
        
        # Verify Logs (Plot)
        self.assertLogExists(LogType.CROWS_PLOT, player=self.player, clearing_number=self.c1.clearing_number)

    def test_drawing_1_plus_extortion(self):
        # Advanced to DRAWING
        self.evening.step = CrowEvening.CrowEveningSteps.DRAWING
        self.evening.save()
        
        p1 = PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.EXTORTION).first()
        p1.clearing = self.c2
        p1.is_facedown = False
        p1.save()
        
        from game.transactions.crows.turn import step_effect
        self.daylight.refresh_from_db()
        self.birdsong.refresh_from_db()
        step_effect(self.player)
        
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.cards_drawn, 2)
        self.assertEqual(self.evening.step, CrowEvening.CrowEveningSteps.COMPLETED)
        
        # Verify Logs (Draw)
        self.assertLogExists(LogType.DRAW, player=self.player, count=2)

    def test_drawing_1_plus_extortion_facedown_does_not_count(self):
        self.evening.step = CrowEvening.CrowEveningSteps.DRAWING
        self.evening.save()
        
        p1 = PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.EXTORTION).first()
        p1.clearing = self.c2
        p1.is_facedown = True
        p1.save()
        
        from game.transactions.crows.turn import step_effect
        self.daylight.refresh_from_db()
        self.birdsong.refresh_from_db()
        step_effect(self.player)
        
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.cards_drawn, 1)
        self.assertEqual(self.evening.step, CrowEvening.CrowEveningSteps.COMPLETED)
        
    def test_drawing_skipped_if_exerted(self):
        self.evening.step = CrowEvening.CrowEveningSteps.DRAWING
        self.evening.exert_used = True
        self.evening.save()
        
        from game.transactions.crows.turn import step_effect
        self.daylight.refresh_from_db()
        self.birdsong.refresh_from_db()
        step_effect(self.player)
        
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.cards_drawn, 0)
        self.assertEqual(self.evening.step, CrowEvening.CrowEveningSteps.COMPLETED)

    def test_discarding_skips_if_under_5(self):
        self.evening.step = CrowEvening.CrowEveningSteps.DISCARDING
        self.evening.save()
        
        # hand size is 0 initially
        check_discard_step(self.player)
        
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, CrowEvening.CrowEveningSteps.COMPLETED)

    def test_discarding_works(self):
        self.evening.step = CrowEvening.CrowEveningSteps.DISCARDING
        self.evening.save()
        
        HandEntry.objects.filter(player=self.player).delete()
        
        from game.tests.my_factories import CardFactory
        c1 = CardFactory(game=self.game, card_type=CardsEP.MOUSE_PARTISANS.name)
        c2 = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name)
        c3 = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        c4 = CardFactory(game=self.game, card_type=CardsEP.COFFIN_MAKERS.name)
        c5 = CardFactory(game=self.game, card_type=CardsEP.CORVID_PLANNERS.name)
        c6 = CardFactory(game=self.game, card_type=CardsEP.SMUGGLERS_TRAIL.name)
        HandEntry.objects.create(player=self.player, card=c1)
        HandEntry.objects.create(player=self.player, card=c2)
        HandEntry.objects.create(player=self.player, card=c3)
        HandEntry.objects.create(player=self.player, card=c4)
        HandEntry.objects.create(player=self.player, card=c5)
        HandEntry.objects.create(player=self.player, card=c6)
        
        # 6 cards, shouldn't skip
        check_discard_step(self.player)
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, CrowEvening.CrowEveningSteps.DISCARDING)
        
        discard_card(self.player, CardsEP.MOUSE_PARTISANS)
        
        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, CrowEvening.CrowEveningSteps.COMPLETED)
