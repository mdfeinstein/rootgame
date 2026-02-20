from django.test import TestCase
from unittest.mock import patch
from game.models.game_models import Faction, Clearing, Warrior, Card, HandEntry
from game.models.events.battle import Battle
from game.models.events.event import Event
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, WarriorFactory
from game.transactions.battle import (
    start_battle, defender_ambush_choice, attacker_ambush_choice, 
    roll_dice, apply_dice_hits
)
from game.game_data.cards.exiles_and_partisans import CardsEP

class BattleTransactionTests(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE])
        self.cats = self.game.players.get(faction=Faction.CATS)
        self.birds = self.game.players.get(faction=Faction.BIRDS)
        self.wa = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)
        
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1) # Fox (Cat Keep)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2) # Mouse
        
        # Clear existing pieces to have clean state for tests
        # We delete Warriors, Wood, and Sympathy, but NOT essential setup pieces (except Keep which we handle)
        Warrior.objects.filter(clearing__in=[self.c1, self.c2]).delete()
        from game.models.wa.tokens import WASympathy
        from game.models.cats.tokens import CatWood, CatKeep
        from game.models.cats.buildings import Recruiter, Sawmill, Workshop
        WASympathy.objects.filter(clearing__in=[self.c1, self.c2]).delete()
        CatWood.objects.filter(clearing__in=[self.c1, self.c2]).delete()
        CatKeep.objects.filter(clearing__in=[self.c1, self.c2]).delete()
        Recruiter.objects.filter(building_slot__clearing__in=[self.c1, self.c2]).delete()
        Sawmill.objects.filter(building_slot__clearing__in=[self.c1, self.c2]).delete()
        Workshop.objects.filter(building_slot__clearing__in=[self.c1, self.c2]).delete()
        
    def test_battle_basic_flow(self):
        # Setup: Cats attacking Birds in C1
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        self.assertEqual(battle.step, Battle.BattleSteps.DEFENDER_AMBUSH_CHECK)
        
        # Defender (Birds) chooses no ambush
        defender_ambush_choice(self.game, battle, None)
        battle.refresh_from_db()
        # Should have rolled dice. Mocking required for predictability.
        # But let's see where it landed.
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED)
        
    @patch('game.transactions.battle.randint')
    def test_battle_dice_and_removal(self, mock_randint):
        # Mock dice: Attacker 3, Defender 1
        mock_randint.side_effect = [3, 1]
        
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        
        defender_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        # High (3) to defender hits, Lo (1) to attacker hits
        # Limited by warrior counts: Attacker has 3, Defender has 2.
        # Defender hits = min(3, 3) = 3. 
        # But wait, defender only has 2 warriors. apply_dice_hits should remove them.
        # Attacker hits = min(1, 2) = 1.
        
        self.assertEqual(battle.defender_hits_taken, 3) 
        self.assertEqual(battle.attacker_hits_taken, 1)
        
        # Check piece counts
        self.assertEqual(Warrior.objects.filter(player=self.cats, clearing=self.c1).count(), 2) # 3 - 1
        self.assertEqual(Warrior.objects.filter(player=self.birds, clearing=self.c1).count(), 0) # 2 - 3 (capped at 0)

    @patch('game.transactions.battle.randint')
    def test_battle_ambush(self, mock_randint):
        # Mock dice 0-0 to only test ambush effect
        mock_randint.side_effect = [0, 0]
        # Defender has ambush card matching C1 (Fox/Red)
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        ambush_fox = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.birds, card=ambush_fox)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        
        # Defender plays ambush
        defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)
        
        battle.refresh_from_db()
        self.assertTrue(battle.defender_ambush)
        self.assertEqual(battle.step, Battle.BattleSteps.ATTACKER_AMBUSH_CANCEL_CHECK)
        
        # Attacker (Cats) has no ambush, proceed
        attacker_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        # Ambush deals 2 hits to attacker
        # Cats should have 3 - 2 = 1 warrior left
        self.assertEqual(Warrior.objects.filter(player=self.cats, clearing=self.c1).count(), 1)
        # Battle continues to ROLL_DICE if attacker has warriors left
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED) # Wait, roll_dice might have finished it if results were low.
        
    @patch('game.transactions.battle.randint')
    def test_battle_wa_guerilla(self, mock_randint):
        # WA defending in C2 (Mouse)
        # WA always takes higher die, attacker takes lower
        mock_randint.side_effect = [3, 1] # High 3, Low 1
        
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c2)
        WarriorFactory.create_batch(2, player=self.wa, clearing=self.c2)
        
        start_battle(self.game, Faction.CATS, Faction.WOODLAND_ALLIANCE, self.c2)
        battle = Battle.objects.get(clearing=self.c2)
        
        defender_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        # WA is defender. 
        # In roll_dice:
        # if battle.defender == Faction.WOODLAND_ALLIANCE:
        #    hi = min(hi, defending_warriors_count) # min(3, 2) = 2
        #    lo = min(lo, attacking_warriors_count) # min(1, 3) = 1
        #    battle.attacker_hits_taken += hi # Attacker takes 2
        #    battle.defender_hits_taken += lo # Defender takes 1
        
        self.assertEqual(battle.attacker_hits_taken, 2)
        self.assertEqual(battle.defender_hits_taken, 1)
        
        self.assertEqual(Warrior.objects.filter(player=self.cats, clearing=self.c2).count(), 1)
        self.assertEqual(Warrior.objects.filter(player=self.wa, clearing=self.c2).count(), 1)

    @patch('game.transactions.battle.randint')
    def test_battle_ambush_cancel(self, mock_randint):
        # Mock dice 0-0 to only test cancel effect
        mock_randint.side_effect = [0, 0]
        # Defender has ambush, Attacker ALSO has ambush
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        # Birds (defender) have ambush
        ambush_red_1 = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.birds, card=ambush_red_1)
        # Cats (attacker) have ambush
        ambush_red_2 = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.cats, card=ambush_red_2)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        
        # Defender plays ambush
        defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)
        # Attacker plays ambush to CANCEL
        attacker_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)
        
        battle.refresh_from_db()
        self.assertTrue(battle.defender_ambush)
        self.assertTrue(battle.attacker_cancel_ambush)
        # Hits should be 0 from ambush
        self.assertEqual(Warrior.objects.filter(player=self.cats, clearing=self.c1).count(), 3)
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED)

    @patch('game.transactions.battle.randint')
    def test_battle_extra_hits(self, mock_randint):
        # 0. Mock dice 0-0
        mock_randint.side_effect = [0, 0]
        
        # Setup: Birds (Commander) attacking Cats
        from game.models.birds.player import BirdLeader
        BirdLeader.objects.filter(player=self.birds).update(active=False)
        leader = BirdLeader.objects.get(player=self.birds, leader=BirdLeader.BirdLeaders.COMMANDER)
        leader.active = True
        leader.save()
        
        # Cats have NO warriors, but have a building (Recruiter)
        from game.models.cats.buildings import Recruiter
        from game.models.game_models import BuildingSlot
        slot = BuildingSlot.objects.filter(clearing=self.c1, building=None).first()
        Recruiter.objects.create(player=self.cats, building_slot=slot)
        
        WarriorFactory.create_batch(1, player=self.birds, clearing=self.c1)
        
        start_battle(self.game, Faction.BIRDS, Faction.CATS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        
        defender_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        # 0-0 dice. 
        # +1 for undefended (0 cat warriors)
        # +1 for Commander
        # Total defender_hits_taken = 2
        self.assertEqual(battle.defender_hits_taken, 2)
        # Cat recruiter should be removed and Birds should score 1 VP
        self.assertFalse(Recruiter.objects.filter(player=self.cats, building_slot__clearing=self.c1).exists())
        self.birds.refresh_from_db()
        self.assertEqual(self.birds.score, 1)

    def test_battle_partisans(self):
        # Fox Partisans in Fox clearing (C1)
        from game.models.events.crafted_cards import PartisansEvent
        from game.transactions.battle import use_partisans
        
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        # Cats have Fox Partisans
        from game.models.game_models import CraftedCardEntry
        partisans_card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        CraftedCardEntry.objects.create(player=self.cats, card=partisans_card)
        
        # Cats have some cards in hand to discard
        card1 = CardFactory(game=self.game, card_type=CardsEP.MOUSE_PARTISANS.name) # Mouse (suit o)
        HandEntry.objects.create(player=self.cats, card=card1)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        
        # Mock dice in test or just call roll_dice
        with patch('game.transactions.battle.randint', return_value=0):
            defender_ambush_choice(self.game, battle, None)
        
        # roll_dice should have launched PartisansEvent
        event = PartisansEvent.objects.get(battle=battle)
        self.assertEqual(event.crafted_card_entry.player, self.cats)
        
        # Use partisans
        use_partisans(self.game, battle, event)
        
        battle.refresh_from_db()
        # Extra hit dealt to Birds
        self.assertEqual(battle.defender_hits_taken, 1)
        # Cards not matching Fox (c1.suit) should be discarded. Mouse card is discarded.
        self.assertFalse(HandEntry.objects.filter(player=self.cats, card=card1).exists())
        # Battle completed
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED)

