from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, Suit, Piece
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowTurn, CrowBirdsong
from game.tests.my_factories import GameSetupFactory
from game.transactions.crows.birdsong import flip_plot

class CrowBirdsongTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.CATS, Faction.CROWS])
        self.player = self.game.players.get(faction=Faction.CROWS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        self.game.current_turn = self.player.turn_order
        self.game.save()
        
        self.turn = CrowTurn.create_turn(self.player)
        self.birdsong = self.turn.birdsong.first()
        
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2)

    def test_flip_plot_requires_warrior(self):
        p1 = PlotToken.objects.filter(player=self.player).first()
        p1.clearing = self.c2 
        p1.is_facedown = True
        p1.save()
        
        self.birdsong.step = CrowBirdsong.CrowBirdsongSteps.FLIP
        self.birdsong.save()
        
        with self.assertRaisesMessage(ValueError, "Must have a Crow warrior present to flip a plot token"):
            flip_plot(self.player, p1)
        
        w = Warrior.objects.filter(player=self.player, clearing__isnull=True).first()
        w.clearing = self.c2
        w.save()
        
        flip_plot(self.player, p1)
        p1.refresh_from_db()
        self.assertFalse(p1.is_facedown)
        self.assertEqual(self.player.score, 1)

    def test_flip_plot_bomb_resolves(self):
        p1 = PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.BOMB).first()
        p1.clearing = self.c2 
        p1.is_facedown = True
        p1.save()
        w = Warrior.objects.filter(player=self.player, clearing__isnull=True).first()
        w.clearing = self.c2
        w.save()
        
        Warrior.objects.create(player=self.cats_player, clearing=self.c2)
        Warrior.objects.create(player=self.cats_player, clearing=self.c2)
        
        self.birdsong.step = CrowBirdsong.CrowBirdsongSteps.FLIP
        self.birdsong.save()
        
        flip_plot(self.player, p1)
        self.assertEqual(Warrior.objects.filter(player=self.cats_player, clearing=self.c2).count(), 0)
