from django.test import TestCase
from unittest.mock import patch
from game.models.game_models import Faction, Clearing, Warrior, Card, HandEntry
from game.models.events.battle import Battle
from game.models.events.event import Event
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, WarriorFactory
from game.transactions.battle import (
    start_battle, defender_ambush_choice, attacker_ambush_choice, 
    attacker_choose_ambush_hit, roll_dice, apply_dice_hits,
    defender_chooses_hit, attacker_chooses_hit
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
        HandEntry.objects.all().delete()
        from game.models.wa.tokens import WASympathy
        from game.models.cats.tokens import CatWood, CatKeep
        from game.models.cats.buildings import Recruiter, Sawmill, Workshop
        WASympathy.objects.filter(clearing__in=[self.c1, self.c2]).delete()
        CatWood.objects.filter(clearing__in=[self.c1, self.c2]).delete()
        CatKeep.objects.filter(clearing__in=[self.c1, self.c2]).delete()
        Recruiter.objects.filter(building_slot__clearing__in=[self.c1, self.c2]).delete()
        Sawmill.objects.filter(building_slot__clearing__in=[self.c1, self.c2]).delete()
        Sawmill.objects.filter(building_slot__clearing__in=[self.c1, self.c2]).delete()
        Workshop.objects.filter(building_slot__clearing__in=[self.c1, self.c2]).delete()
        
    def test_battle_start_fails_same_faction(self):
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        with self.assertRaisesRegex(ValueError, "Attacker and defender cannot be the same faction"):
            start_battle(self.game, Faction.CATS, Faction.CATS, self.c1)

    def test_battle_start_fails_attacker_no_warriors(self):
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        with self.assertRaisesRegex(ValueError, "Attacker does not have warriors in that clearing"):
            start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)

    def test_battle_start_fails_defender_no_pieces(self):
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        with self.assertRaisesRegex(ValueError, "Defender does not have pieces in that clearing"):
            start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)

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
    def test_roll_dice_standard_full_hits(self, mock_randint):
        mock_randint.side_effect = [3, 2]
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(3, player=self.birds, clearing=self.c1)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        
        self.assertEqual(battle.defender_hits_taken, 3) 
        self.assertEqual(battle.attacker_hits_taken, 2)
        self.assertEqual(Warrior.objects.filter(player=self.cats, clearing=self.c1).count(), 1)
        self.assertEqual(Warrior.objects.filter(player=self.birds, clearing=self.c1).count(), 0)

    @patch('game.transactions.battle.randint')
    def test_roll_dice_standard_attacker_capped(self, mock_randint):
        mock_randint.side_effect = [3, 1]
        WarriorFactory.create_batch(2, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(3, player=self.birds, clearing=self.c1)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        
        # Attacker rolled 3 but only has 2 warriors, hits dealt to defender capped at 2.
        self.assertEqual(battle.defender_hits_taken, 2) 
        self.assertEqual(battle.attacker_hits_taken, 1)
        self.assertEqual(Warrior.objects.filter(player=self.cats, clearing=self.c1).count(), 1)
        self.assertEqual(Warrior.objects.filter(player=self.birds, clearing=self.c1).count(), 1)

    @patch('game.transactions.battle.randint')
    def test_roll_dice_standard_defender_capped(self, mock_randint):
        mock_randint.side_effect = [3, 2]
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(1, player=self.birds, clearing=self.c1)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        
        # Defender has 1 warrior, so they take 3 hits, but only cap 1 hit against attacker
        self.assertEqual(battle.defender_hits_taken, 3) 
        self.assertEqual(battle.attacker_hits_taken, 1)
        self.assertEqual(Warrior.objects.filter(player=self.cats, clearing=self.c1).count(), 2)
        self.assertEqual(Warrior.objects.filter(player=self.birds, clearing=self.c1).count(), 0)

    @patch('game.transactions.battle.randint')
    def test_roll_dice_wa_defender(self, mock_randint):
        mock_randint.side_effect = [3, 1]  # Attacker rolls 3, Defender rolls 1
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(3, player=self.wa, clearing=self.c1)
        
        start_battle(self.game, Faction.CATS, Faction.WOODLAND_ALLIANCE, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        # WA defender gets the higher roll (3), Attacker gets lower (1) -> hits capped by 3 warriors each.
        self.assertEqual(battle.defender_hits_taken, 1) 
        self.assertEqual(battle.attacker_hits_taken, 3)
        self.assertEqual(Warrior.objects.filter(player=self.cats, clearing=self.c1).count(), 0) # 3 - 3 = 0
        self.assertEqual(Warrior.objects.filter(player=self.wa, clearing=self.c1).count(), 2) # 3 - 1 = 2

    @patch('game.transactions.battle.randint')
    def test_roll_dice_eyrie_commander(self, mock_randint):
        mock_randint.side_effect = [1, 1]  # Roll 1 each
        
        from game.models.birds.player import BirdLeader
        # deactivate current leader
        current_leader = BirdLeader.objects.get(player=self.birds, active=True)
        current_leader.active = False
        current_leader.save()
        # assign Commander leader
        BirdLeader.objects.create(player=self.birds, leader=BirdLeader.BirdLeaders.COMMANDER, active=True)
        
        WarriorFactory.create_batch(3, player=self.birds, clearing=self.c1)
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        
        start_battle(self.game, Faction.BIRDS, Faction.CATS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        # Attacker gets 1 + 1 (Commander) = 2 hits. Defender gets 1 hit.
        self.assertEqual(battle.defender_hits_taken, 2) 
        self.assertEqual(battle.attacker_hits_taken, 1)

    @patch('game.transactions.battle.randint')
    def test_roll_dice_transitions_to_defender_choose_hits(self, mock_randint):
        mock_randint.side_effect = [2, 0]  # Attacker rolls 2, Defender rolls 0
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(1, player=self.birds, clearing=self.c1)
        
        from game.models.birds.buildings import BirdRoost
        from game.models.game_models import BuildingSlot
        s1 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=1)
        s2 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=2)
        BirdRoost.objects.create(player=self.birds, building_slot=s1)
        BirdRoost.objects.create(player=self.birds, building_slot=s2)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        # Takes 2 hits. 1 warrior is destroyed. 1 hit left, 2 buildings remaining.
        # Should transition to defender choose hits.
        self.assertEqual(Warrior.objects.filter(player=self.birds, clearing=self.c1).count(), 0)
        self.assertEqual(battle.step, Battle.BattleSteps.DEFENDER_CHOOSE_HITS)
        # Verify defender hits assigned is 1 (for the warrior)
        self.assertEqual(battle.defender_hits_assigned, 1)

    @patch('game.transactions.battle.randint')
    def test_choose_hits_after_battle(self, mock_randint):
        mock_randint.side_effect = [3, 2]  # Attacker rolls 3, Defender rolls 2
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(1, player=self.birds, clearing=self.c1)
        
        from game.models.birds.buildings import BirdRoost
        from game.models.game_models import BuildingSlot
        s1 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=1)
        s2 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=2)
        s3_def = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=3)
        roost1 = BirdRoost.objects.create(player=self.birds, building_slot=s1)
        roost2 = BirdRoost.objects.create(player=self.birds, building_slot=s2)
        roost3 = BirdRoost.objects.create(player=self.birds, building_slot=s3_def)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.DEFENDER_CHOOSE_HITS)
        
        # Defender chooses hit
        defender_chooses_hit(self.game, battle, roost1)
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.DEFENDER_CHOOSE_HITS)
        self.assertEqual(battle.defender_hits_assigned, 2)
        
        from game.models.cats.buildings import Recruiter
        s3 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=3)
        recruiter = Recruiter.objects.create(player=self.cats, building_slot=s3)
        with self.assertRaisesRegex(ValueError, "Piece must belong to the defender"):
            defender_chooses_hit(self.game, battle, recruiter)
        
        # Defender chooses another hit
        defender_chooses_hit(self.game, battle, roost2)
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED)

    @patch('game.transactions.battle.randint')
    def test_attacker_choose_hits_after_battle(self, mock_randint):
        mock_randint.side_effect = [2, 3]  
        WarriorFactory.create_batch(1, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(3, player=self.birds, clearing=self.c1)
        
        from game.models.birds.buildings import BirdRoost
        from game.models.game_models import BuildingSlot
        from game.models.cats.buildings import Recruiter, Sawmill
        s1 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=1)
        s3_att = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=3)
        s4_att = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=4)
        roost1 = BirdRoost.objects.create(player=self.birds, building_slot=s1)
        recruiter = Recruiter.objects.create(player=self.cats, building_slot=s3_att)
        sawmill = Sawmill.objects.create(player=self.cats, building_slot=s4_att)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, None)
        
        battle.refresh_from_db()
        # Attacker hits defender for min(3, 1) = 1. Defender warrior takes it.
        # Defender hits attacker for min(2, 3) = 2.
        # Attacker has 1 warrior. Takes 2 hits. 1 warrior destroyed. 1 hit left. Recruiter+Sawmill are 2 pieces. 
        self.assertEqual(battle.step, Battle.BattleSteps.ATTACKER_CHOOSE_HITS)
        
        # Validation checks
        with self.assertRaisesRegex(ValueError, "Piece must belong to the attacker"):
            attacker_chooses_hit(self.game, battle, roost1)
            
        attacker_chooses_hit(self.game, battle, recruiter)
        
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED)

    def test_defender_ambush_fails_wrong_timing(self):
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        battle.step = Battle.BattleSteps.ROLL_DICE
        battle.save()
        
        with self.assertRaisesRegex(ValueError, "Not defender ambush check step"):
            defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)

    def test_defender_ambush_fails_not_ambush_card(self):
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        card = CardFactory(game=self.game, card_type=CardsEP.FOXFOLK_STEEL.name)
        HandEntry.objects.create(player=self.birds, card=card)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        
        with self.assertRaisesRegex(ValueError, "Card is not an ambush"):
            defender_ambush_choice(self.game, battle, CardsEP.FOXFOLK_STEEL)

    def test_defender_ambush_fails_not_in_hand(self):
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        
        with self.assertRaisesRegex(ValueError, "Player does not have card in hand"):
            defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)

    def test_attacker_ambush_fails_wrong_timing(self):
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        # It's currently DEFENDER_AMBUSH_CHECK
        with self.assertRaisesRegex(ValueError, "Not attacker ambush cancel check step"):
            attacker_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)

    def test_attacker_ambush_fails_not_ambush_card(self):
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        ambush_red = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.birds, card=ambush_red)
        
        non_ambush = CardFactory(game=self.game, card_type=CardsEP.FOXFOLK_STEEL.name)
        HandEntry.objects.create(player=self.cats, card=non_ambush)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)
        
        with self.assertRaisesRegex(ValueError, "Card is not an ambush"):
            attacker_ambush_choice(self.game, battle, CardsEP.FOXFOLK_STEEL)

    @patch('game.transactions.battle.randint')
    def test_attacker_ambush_counter_played(self, mock_randint):
        mock_randint.side_effect = [0, 0]
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        ambush_red_1 = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.birds, card=ambush_red_1)
        ambush_red_2 = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.cats, card=ambush_red_2)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)
        
        attacker_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED) # Completes as 0-0 hits
        self.assertFalse(HandEntry.objects.filter(card=ambush_red_2).exists())
        self.assertTrue(battle.attacker_cancel_ambush)

    @patch('game.transactions.battle.randint')
    def test_attacker_ambush_no_counter_losses_2_warriors(self, mock_randint):
        mock_randint.side_effect = [0, 0]
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        ambush_red = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.birds, card=ambush_red)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)
        
        attacker_ambush_choice(self.game, battle, None)
        battle.refresh_from_db()
        
        self.assertEqual(Warrior.objects.filter(player=self.cats, clearing=self.c1).count(), 1)
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED)

    @patch('game.transactions.battle.randint')
    def test_attacker_ambush_no_counter_2_warriors_ends_battle(self, mock_randint):
        mock_randint.side_effect = [0, 0]
        WarriorFactory.create_batch(2, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        ambush_red = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.birds, card=ambush_red)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)
        
        attacker_ambush_choice(self.game, battle, None)
        battle.refresh_from_db()
        
        self.assertEqual(Warrior.objects.filter(player=self.cats, clearing=self.c1).count(), 0)
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED)

    @patch('game.transactions.battle.randint')
    def test_attacker_ambush_no_counter_losses_1_warrior_and_chooses(self, mock_randint):
        mock_randint.side_effect = [0, 0]
        WarriorFactory.create_batch(1, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        from game.models.cats.buildings import Recruiter, Sawmill
        from game.models.game_models import BuildingSlot
        # create two slot explicitly
        s1 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=1)
        s2 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=2)

        Recruiter.objects.create(player=self.cats, building_slot=s1)
        Sawmill.objects.create(player=self.cats, building_slot=s2)
        
        ambush_red = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.birds, card=ambush_red)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)
        
        attacker_ambush_choice(self.game, battle, None)
        battle.refresh_from_db()
        
        self.assertEqual(Warrior.objects.filter(player=self.cats, clearing=self.c1).count(), 0)
        self.assertEqual(battle.step, Battle.BattleSteps.ATTACKER_CHOOSE_AMBUSH_HITS)

    @patch('game.transactions.battle.randint')
    def test_attacker_choose_ambush_hit_fails_wrong_piece(self, mock_randint):
        mock_randint.side_effect = [0, 0]
        WarriorFactory.create_batch(1, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        from game.models.cats.buildings import Recruiter
        from game.models.game_models import BuildingSlot
        s1 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=1)
        recruiter = Recruiter.objects.create(player=self.cats, building_slot=s1)
        
        ambush_red = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.birds, card=ambush_red)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)
        attacker_ambush_choice(self.game, battle, None)
        
        # We can't actually pass a warrior here easily because cat warrior was destroyed.
        # So let's create a temp warrior for testing the ValueError.
        temp_warrior = WarriorFactory.create(player=self.cats, clearing=self.c1)
        with self.assertRaisesRegex(ValueError, "Cannot choose a warrior"):
            attacker_choose_ambush_hit(self.game, battle, temp_warrior)
            
        from game.models.birds.buildings import BirdRoost
        s2 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=2)
        roost = BirdRoost.objects.create(player=self.birds, building_slot=s2)
        with self.assertRaisesRegex(ValueError, "Piece must belong to the attacker"):
            attacker_choose_ambush_hit(self.game, battle, roost)

    @patch('game.transactions.battle.randint')
    def test_attacker_choose_ambush_hit_success(self, mock_randint):
        mock_randint.side_effect = [0, 0]
        WarriorFactory.create_batch(1, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        from game.models.cats.buildings import Recruiter
        from game.models.game_models import BuildingSlot
        s1 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=1)
        recruiter = Recruiter.objects.create(player=self.cats, building_slot=s1)
        
        ambush_red = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.birds, card=ambush_red)
        
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        battle = Battle.objects.get(clearing=self.c1)
        defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)
        attacker_ambush_choice(self.game, battle, None)
        
        attacker_choose_ambush_hit(self.game, battle, recruiter)
        
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED)
        from game.models.cats.buildings import Recruiter
        self.assertIsNone(Recruiter.objects.get(pk=recruiter.pk).building_slot)

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
        self.assertFalse(HandEntry.objects.filter(card=ambush_fox).exists())
        
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
        self.assertFalse(HandEntry.objects.filter(card=ambush_red_1).exists())
        self.assertFalse(HandEntry.objects.filter(card=ambush_red_2).exists())
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

