from rest_framework import status
from rest_framework.test import APITestCase
from game.models.game_models import Faction, Clearing, Warrior, Token, Building
from game.models.crows.tokens import PlotToken
from game.models.events.event import Event, EventType
from game.models.events.crows import CrowRaidEvent
from game.tests.my_factories import GameSetupWithFactionsFactory
from game.tests.logging_mixin import LoggingTestMixin
from game.models.game_log import LogType

class CrowPlotTokenEffectsTests(APITestCase, LoggingTestMixin):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.CROWS])
        self.crows_player = self.game.players.get(faction=Faction.CROWS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        
        # Connections for C1 (Autumn map: 1 connects to 5, 2 connects to 1/5/6/10)
        # 1-5, 2-1, 2-5, 2-6, 2-10
        self.c5 = Clearing.objects.get(game=self.game, clearing_number=5)

    def test_bomb_self_removal(self):
        """Verify Bomb removes itself after triggering"""
        from game.transactions.crows.birdsong import resolve_bomb
        
        bomb = PlotToken.objects.filter(player=self.crows_player, plot_type=PlotToken.PlotType.BOMB).first()
        bomb.clearing = self.c1
        bomb.is_facedown = False
        bomb.save()
        
        # Enemy pieces to remove
        Warrior.objects.create(player=self.cats_player, clearing=self.c1)
        
        resolve_bomb(self.crows_player, bomb)
        
        bomb.refresh_from_db()
        self.assertIsNone(bomb.clearing)
        self.assertEqual(Warrior.objects.filter(clearing=self.c1, player=self.cats_player).count(), 0)

    def test_snare_placement_block(self):
        """Verify Snare blocks non-Crow placement"""
        from game.transactions.general import place_piece_from_supply_into_clearing
        
        snare = PlotToken.objects.filter(player=self.crows_player, plot_type=PlotToken.PlotType.SNARE).first()
        snare.clearing = self.c1
        snare.is_facedown = False
        snare.save()
        
        cat_warrior = Warrior.objects.filter(player=self.cats_player, clearing__isnull=True).first()
        
        with self.assertRaisesRegex(ValueError, "Cannot place piece in clearing with a face-up Snare"):
            place_piece_from_supply_into_clearing(cat_warrior, self.c1)

    def test_snare_movement_block(self):
        """Verify Snare blocks enemies from moving OUT"""
        from game.queries.general import validate_legal_move
        
        snare = PlotToken.objects.filter(player=self.crows_player, plot_type=PlotToken.PlotType.SNARE).first()
        snare.clearing = self.c1
        snare.is_facedown = False
        snare.save()
        
        cat_warrior = Warrior.objects.create(player=self.cats_player, clearing=self.c1)
        
        with self.assertRaisesRegex(ValueError, "Cannot move out of a clearing with a face-up Snare"):
            validate_legal_move(self.cats_player, self.c1, self.c5)

    def test_raid_auto_placement(self):
        """Verify Raid auto-places warriors if supply is sufficient"""
        from game.transactions.removal import player_removes_token
        
        raid = PlotToken.objects.filter(player=self.crows_player, plot_type=PlotToken.PlotType.RAID).first()
        raid.clearing = self.c1
        raid.save()
        
        # Connection for C1 is C5 (Autumn map)
        # Ensure C5 is valid for placement
        
        initial_warriors_in_c5 = Warrior.objects.filter(clearing=self.c5, player=self.crows_player).count()
        
        player_removes_token(self.game, raid, self.cats_player, is_exposure=False)
        
        self.assertEqual(Warrior.objects.filter(clearing=self.c5, player=self.crows_player).count(), initial_warriors_in_c5 + 1)
        # VERIFY LOG
        self.assertLogExists(LogType.CROWS_RAID, player=self.crows_player, origin_clearing_number=self.c1.clearing_number)

    def test_raid_manual_placement_event(self):
        """Verify Raid launches event if supply is insufficient"""
        from game.transactions.removal import player_removes_token
        
        raid = PlotToken.objects.filter(player=self.crows_player, plot_type=PlotToken.PlotType.RAID).first()
        raid.clearing = self.c1
        raid.save()
        
        # Empty Crows supply
        Warrior.objects.filter(player=self.crows_player, clearing__isnull=True).delete()
        
        player_removes_token(self.game, raid, self.cats_player, is_exposure=False)
        
        event = Event.objects.filter(game=self.game, type=EventType.PLACE_RAID_WARRIORS, is_resolved=False).first()
        self.assertIsNotNone(event)
        
        raid_event = CrowRaidEvent.objects.get(event=event)
        self.assertIn(self.c5, raid_event.remaining_clearings.all())
