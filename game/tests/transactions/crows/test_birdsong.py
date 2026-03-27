from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, Suit, Piece, HandEntry
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowTurn, CrowBirdsong
from game.tests.my_factories import GameSetupFactory, CardFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.crows.birdsong import flip_plot, crows_craft_card, crows_recruit
from game.tests.logging_mixin import LoggingTestMixin
from game.models.game_log import LogType

class CrowBirdsongTestCase(LoggingTestMixin, TestCase):
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
        
        # Verify Logs
        self.assertLogExists(LogType.CROWS_FLIP, player=self.player, clearing_number=self.c2.clearing_number)

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
        
        # Verify Logs
        self.assertLogExists(LogType.CROWS_FLIP, player=self.player, plot_type="bomb")
        self.assertLogExists(LogType.PIECE_REMOVAL, player=self.player, count=2, piece_type="Warrior")

    def test_flip_plot_extortion_resolves(self):
        p1 = PlotToken.objects.filter(player=self.player, plot_type=PlotToken.PlotType.EXTORTION).first()
        p1.clearing = self.c2 
        p1.is_facedown = True
        p1.save()
        w = Warrior.objects.filter(player=self.player, clearing__isnull=True).first()
        w.clearing = self.c2
        w.save()
        
        # Give cats exactly one card
        HandEntry.objects.filter(player=self.cats_player).delete()
        cat_card = CardFactory(game=self.game, card_type=CardsEP.MOUSE_PARTISANS.name)
        HandEntry.objects.create(player=self.cats_player, card=cat_card)
        # Ensure cats have pieces in clearing
        Warrior.objects.create(player=self.cats_player, clearing=self.c2)
        
        self.birdsong.step = CrowBirdsong.CrowBirdsongSteps.FLIP
        self.birdsong.save()
        
        flip_plot(self.player, p1)
        
        # Check card stolen
        self.assertTrue(HandEntry.objects.filter(player=self.player, card=cat_card).exists())
        # Verify Logs
        self.assertLogExists(LogType.CROWS_EXTORTION_STOLE_CARD, player=self.player, victim_faction=Faction.CATS.value)

    def test_craft_card_success(self):
        p1 = PlotToken.objects.filter(player=self.player).first()
        p1.clearing = self.c1
        p1.is_facedown = True
        p1.save()
        
        self.c1.suit = Suit.RED.value
        self.c1.save()
        
        card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        he = HandEntry.objects.create(player=self.player, card=card)
        
        self.birdsong.step = CrowBirdsong.CrowBirdsongSteps.CRAFT
        self.birdsong.save()
        
        crows_craft_card(self.player, CardsEP.FOX_PARTISANS, [p1])
        
        # Verify Logs
        self.assertLogExists(LogType.CRAFT, player=self.player)

    def test_recruit_success(self):
        card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        he = HandEntry.objects.create(player=self.player, card=card)
        
        self.birdsong.step = CrowBirdsong.CrowBirdsongSteps.RECRUIT
        self.birdsong.save()
        
        fox_clearings = list(Clearing.objects.filter(game=self.game, suit=Suit.RED.value))
        crows_recruit(self.player, CardsEP.FOX_PARTISANS)
        
        # Verify logs
        self.assertLogExists(LogType.CROWS_RECRUIT, player=self.player, clearing_count=len(fox_clearings))
