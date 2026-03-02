from game.transactions.general import place_warriors_into_clearing
from game.models import CatKeep
from game.models.crows import CrowDaylight
from game.queries.crows.turn import validate_turn
from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, Suit, Piece
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowTurn
from game.tests.my_factories import GameSetupFactory
from game.transactions.crows.actions import crows_plot, crows_move, crows_trick

class CrowActionsTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.CATS, Faction.CROWS])
        self.player = self.game.players.get(faction=Faction.CROWS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        self.game.current_turn = self.player.turn_order
        self.game.save()
        CrowTurn.create_turn(self.player)
        self.turn = validate_turn(self.player)
        self.daylight = CrowDaylight.objects.get(turn=self.turn)
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        self.c1.connected_clearings.add(self.c2)
        self.c2.connected_clearings.add(self.c1)
        
        c1_ids = list(Warrior.objects.filter(player=self.player).values_list('id', flat=True)[:5])
        Warrior.objects.filter(id__in=c1_ids).update(clearing=self.c1)
        c2_ids = list(Warrior.objects.filter(player=self.player, clearing__isnull=True).values_list('id', flat=True)[:2])
        Warrior.objects.filter(id__in=c2_ids).update(clearing=self.c2)

    def test_crows_plot_success_and_cost_scaling(self):
        plot_type = PlotToken.PlotType.BOMB
        crows_plot(self.player, self.c2, plot_type, daylight=self.daylight)
        
        plot = PlotToken.objects.get(clearing=self.c2)
        self.assertTrue(plot.is_facedown)
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.plots_placed, 1)
        self.assertEqual(Warrior.objects.filter(clearing=self.c2, player=self.player).count(), 1)
        
        #make sure only one warrior in c1, and no catkeep
        CatKeep.objects.filter(clearing=self.c1).delete()
        Warrior.objects.filter(clearing=self.c1, player=self.player).update(clearing=None)
        place_warriors_into_clearing(self.player, self.c1, 1)
        self.assertEqual(Warrior.objects.filter(clearing=self.c1, player=self.player).count(), 1)
        # Another plot should cost 2, so this should fail
        with self.assertRaises(ValueError):
            crows_plot(self.player, self.c1, PlotToken.PlotType.SNARE, daylight=self.daylight)
        # add another warrior to c1 (making it 2) and now it should succeed, and there should be no warriors left
        place_warriors_into_clearing(self.player, self.c1, 1)
        crows_plot(self.player, self.c1, PlotToken.PlotType.SNARE, daylight=self.daylight)
        self.assertEqual(self.daylight.plots_placed, 2)
        self.assertEqual(Warrior.objects.filter(clearing=self.c1, player=self.player).count(), 0)

    def test_crows_plot_failures(self):
        # 1. token not in supply
        PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.BOMB).update(clearing=self.c1)
        with self.assertRaisesMessage(ValueError, "No plot token of type bomb available in supply"):
            crows_plot(self.player, self.c2, PlotToken.PlotType.BOMB)

        # restore token
        PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.BOMB).update(clearing=None)

        # 2. already a token here
        PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.SNARE).update(clearing=self.c2)
        with self.assertRaisesMessage(ValueError, "Clearing already has a plot token"):
            crows_plot(self.player, self.c2, PlotToken.PlotType.BOMB)

    def test_crows_move_ignores_rule(self):
        for _ in range(10): Warrior.objects.create(player=self.cats_player, clearing=self.c1)
        for _ in range(10): Warrior.objects.create(player=self.cats_player, clearing=self.c2)
        
        from game.queries.general import determine_clearing_rule
        self.assertEqual(determine_clearing_rule(self.c1), self.cats_player)
        
        crows_move(self.player, self.c1, self.c2, 1)
        self.assertEqual(Warrior.objects.filter(clearing=self.c2, player=self.player).count(), 3)

    def test_crows_trick_both_facedown_success(self):
        p1 = PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.BOMB).first()
        p2 = PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.SNARE).first()
        p1.clearing, p2.clearing = self.c1, self.c2
        p1.is_facedown = True
        p2.is_facedown = True
        p1.save()
        p2.save()
        
        crows_trick(self.player, p1, p2)
        self.assertEqual(p1.clearing, self.c2)
        self.assertEqual(p2.clearing, self.c1)

    def test_crows_trick_failures_and_faceup_success(self):
        p1 = PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.BOMB).first()
        p2 = PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.SNARE).first()
        
        # one not on board
        with self.assertRaisesMessage(ValueError, "Both plot tokens must be on the board"):
            crows_trick(self.player, p1, p2)
            
        p1.clearing = self.c1
        p2.clearing = self.c2
        p1.save()
        p2.save()
        
        # mixed
        p1.is_facedown = False
        p2.is_facedown = True
        p1.save()
        p2.save()
        with self.assertRaisesMessage(ValueError, "Both plot tokens must be in the same state (both facedown or both faceup)"):
            crows_trick(self.player, p1, p2)
            
        # succeeds when both face up
        p2.is_facedown = False
        p2.save()
        crows_trick(self.player, p1, p2)
        self.assertEqual(p1.clearing, self.c2)
        self.assertEqual(p2.clearing, self.c1)
