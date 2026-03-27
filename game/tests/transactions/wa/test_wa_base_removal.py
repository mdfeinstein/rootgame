from django.test import TestCase
from game.models import (
    Faction,
    Game,
    Player,
    Clearing,
    Suit,
    Warrior,
)
from game.models.wa.buildings import WABase
from game.models.wa.player import SupporterStackEntry, OfficerEntry
from game.tests.my_factories import (
    GameSetupWithFactionsFactory,
    CardFactory,
    WarriorFactory,
)
from game.transactions.removal import player_removes_building
from game.tests.logging_mixin import LoggingTestMixin
from game.models.game_log import LogType

class WABaseRemovalTests(TestCase, LoggingTestMixin):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.WOODLAND_ALLIANCE])
        self.wa_player = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Fox clearing with slot
        self.fox_clearing = Clearing.objects.filter(game=self.game, suit=Suit.RED).first()
        from game.models import BuildingSlot
        if not BuildingSlot.objects.filter(clearing=self.fox_clearing).exists():
            BuildingSlot.objects.create(clearing=self.fox_clearing, building_slot_number=0)
        self.slot = self.fox_clearing.buildingslot_set.first()
        # Clear existing buildings from this clearing
        from game.models import Building
        Building.objects.filter(building_slot__clearing=self.fox_clearing).delete()

    def test_base_removal_penalties(self):
        # 1. Setup: WA has a Fox base, 3 Fox supporters, 3 officers
        base = WABase.objects.get(player=self.wa_player, suit=Suit.RED)
        base.building_slot = self.slot
        base.save()
        
        # Clear any global supporters
        SupporterStackEntry.objects.filter(player=self.wa_player).delete()
        
        # Add supporters (2 fox, 1 bird, 1 mouse)
        from game.game_data.cards.exiles_and_partisans import CardsEP
        fox1 = CardFactory(game=self.game, card_type=CardsEP.FOXFOLK_STEEL.name)
        fox2 = CardFactory(game=self.game, card_type=CardsEP.EYRIE_EMIGRE.name)
        bird1 = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_WILD.name)
        mouse1 = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_ORANGE.name)
        
        SupporterStackEntry.objects.create(player=self.wa_player, card=fox1)
        SupporterStackEntry.objects.create(player=self.wa_player, card=fox2)
        SupporterStackEntry.objects.create(player=self.wa_player, card=bird1)
        SupporterStackEntry.objects.create(player=self.wa_player, card=mouse1)
        
        # Add 3 officers
        for _ in range(3):
            warrior = WarriorFactory(player=self.wa_player, clearing=None)
            OfficerEntry.objects.create(player=self.wa_player, warrior=warrior)
            
        # 2. Remove base
        player_removes_building(self.game, base, self.cats_player)
        
        # 3. Verify penalties
        # Supporters: Fox and Bird should be gone. Mouse should remain.
        self.assertEqual(SupporterStackEntry.objects.filter(player=self.wa_player).count(), 1)
        remaining = SupporterStackEntry.objects.get(player=self.wa_player)
        self.assertEqual(remaining.card.title, "Ambush!")
        
        # Officers: 3 -> lost 2 (half rounded up) -> 1 remains
        self.assertEqual(OfficerEntry.objects.filter(player=self.wa_player).count(), 1)
        
        # Verify Logs
        self.assertLogExists(LogType.WA_BASE_REMOVED, player=self.wa_player, suit=Suit.RED)
        self.assertLogExists(LogType.WA_OFFICERS_LOST, player=self.wa_player, count=2)
        self.assertLogExists(LogType.WA_SUPPORTERS_LOST, player=self.wa_player)
        
        # Verify piece removal log too
        self.assertLogExists(LogType.PIECE_REMOVAL, player=self.cats_player, piece_type="Base")
