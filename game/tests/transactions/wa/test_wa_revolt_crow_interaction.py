from django.test import TestCase
from game.models import Game, Player, Clearing, Warrior, Faction
from game.models.wa.tokens import WASympathy
from game.models.crows.tokens import PlotToken
from game.models.wa.player import SupporterStackEntry
from game.models.game_log import GameLog, LogType
from game.transactions.wa import revolt
from game.tests.my_factories import GameSetupWithFactionsFactory
from game.tests.logging_mixin import LoggingTestMixin

class WARevoltCrowInteractionTests(TestCase, LoggingTestMixin):
    def setUp(self):
        # Setup game with WA and Crows (and Cats as a third to ensure full map initialized)
        self.game = GameSetupWithFactionsFactory(factions=[Faction.WOODLAND_ALLIANCE, Faction.CROWS, Faction.CATS])
        self.wa_player = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)
        self.crows_player = self.game.players.get(faction=Faction.CROWS)
        
        self.c11 = Clearing.objects.get(game=self.game, clearing_number=11)
        self.c6 = Clearing.objects.get(game=self.game, clearing_number=6)
        self.c12 = Clearing.objects.get(game=self.game, clearing_number=12)
        self.c3 = Clearing.objects.get(game=self.game, clearing_number=3)
        
        # 1. Place WA Sympathy in clearing 11
        WASympathy.objects.create(player=self.wa_player, clearing=self.c11)
        
        # 2. Place Crow Raid plot in clearing 11
        self.raid = PlotToken.objects.filter(player=self.crows_player, plot_type=PlotToken.PlotType.RAID).first()
        self.raid.clearing = self.c11
        self.raid.is_facedown = False
        self.raid.save()
        
        # 3. Give WA two mouse supporter cards (Clearing 11 is Mouse/Orange)
        from game.models.game_models import Card, Suit
        mouse_cards = Card.objects.filter(suit=Suit.ORANGE)[:2]
        for card in mouse_cards:
            SupporterStackEntry.objects.create(player=self.wa_player, card=card)
            
        # 4. Clear all Crow warriors from board (placed during factory setup)
        Warrior.objects.filter(player=self.crows_player).update(clearing=None)

    def test_revolt_triggers_raid_logic_and_logs(self):
        """
        Verify that a WA revolt in a clearing with a Crow Raid plot triggers the Raid effect
        AND creates properly nested logs.
        """
        # TRIGGER REVOLT
        revolt(self.wa_player, self.c11)
        
        # 1. VERIFY COMPONENT PLACEMENT
        self.assertEqual(Warrior.objects.filter(player=self.crows_player, clearing=self.c6).count(), 1)
        self.assertEqual(Warrior.objects.filter(player=self.crows_player, clearing=self.c12).count(), 1)
        self.assertEqual(Warrior.objects.filter(player=self.crows_player, clearing=self.c3).count(), 1)
        
        # 2. VERIFY LOGS
        # Look for the WA Revolt log
        self.assertLogExists(LogType.WA_REVOLT, player=self.wa_player, clearing_number=11)
        revolt_log = GameLog.objects.get(log_type=LogType.WA_REVOLT, details__clearing_number=11)
        
        # Look for the Crow Raid log, it should be parented to the Revolt log
        self.assertLogExists(LogType.CROWS_RAID, player=self.crows_player, parent=revolt_log, origin_clearing_number=11)
        
        # 3. VERIFY NO DUPLICATE PIECE_REMOVAL LOGS
        # We suppressed individual logs for the pieces removed by the revolt itself (since they are in the revolt summary)
        self.assertLogCount(0, log_type=LogType.PIECE_REMOVAL)
