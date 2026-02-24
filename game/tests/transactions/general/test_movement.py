from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior
from game.tests.my_factories import GameSetupWithFactionsFactory, WarriorFactory
from game.transactions.general import move_warriors

class MovementTests(TestCase):
    def setUp(self):
        # Autumn Map: Cats in 1 (Keep), Birds in 3 (Roost), WA empty
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE])
        self.player_cats = self.game.players.get(faction=Faction.CATS)
        self.player_birds = self.game.players.get(faction=Faction.BIRDS)
        self.player_wa = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)

        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        self.c3 = Clearing.objects.get(game=self.game, clearing_number=3)
        self.c4 = Clearing.objects.get(game=self.game, clearing_number=4)

    def test_move_adjacent_ruled_start_target_enemy_ruled(self):
        # Cats rule 1 (Keep). 1 is adjacent to 5.
        # Make Birds rule 5.
        WarriorFactory(player=self.player_birds, clearing=self.c5)
        WarriorFactory(player=self.player_birds, clearing=self.c5)
        # Cats need warriors in 1 to move.
        if not Warrior.objects.filter(player=self.player_cats, clearing=self.c1).exists():
            WarriorFactory(player=self.player_cats, clearing=self.c1)

        initial_c1 = Warrior.objects.filter(player=self.player_cats, clearing=self.c1).count()
        initial_c5 = Warrior.objects.filter(player=self.player_cats, clearing=self.c5).count()

        # Should succeed because Cats rule start
        move_warriors(self.player_cats, self.c1, self.c5, 1)

        self.assertEqual(Warrior.objects.filter(player=self.player_cats, clearing=self.c1).count(), initial_c1 - 1)
        self.assertEqual(Warrior.objects.filter(player=self.player_cats, clearing=self.c5).count(), initial_c5 + 1)

    def test_move_adjacent_ruled_end_origin_enemy_ruled(self):
        # Cats rule 1 (Keep). 1 is adjacent to 5.
        # Make Birds rule 5.
        WarriorFactory(player=self.player_birds, clearing=self.c5)
        WarriorFactory(player=self.player_birds, clearing=self.c5)
        # Place Cat warriors in 5 (origin) so they can move.
        WarriorFactory(player=self.player_cats, clearing=self.c5)
        
        # Cats move 5 -> 1.
        # Origin (5) is ruled by Birds.
        # Destination (1) is ruled by Cats.
        # Should succeed.
        
        initial_c5 = Warrior.objects.filter(player=self.player_cats, clearing=self.c5).count()
        initial_c1 = Warrior.objects.filter(player=self.player_cats, clearing=self.c1).count()

        move_warriors(self.player_cats, self.c5, self.c1, 1)
        
        self.assertEqual(Warrior.objects.filter(player=self.player_cats, clearing=self.c5).count(), initial_c5 - 1)
        self.assertEqual(Warrior.objects.filter(player=self.player_cats, clearing=self.c1).count(), initial_c1 + 1)

    def test_move_not_adjacent(self):
        # 1 and 3 are not adjacent.
        WarriorFactory(player=self.player_cats, clearing=self.c1)
        
        with self.assertRaisesRegex(ValueError, "not adjacent"):
            move_warriors(self.player_cats, self.c1, self.c3, 1)

    def test_move_noone_rules_either_clearing(self):
        # Setup scenario where Cats move from A to B but rule neither.
        # Using WA to tie or rule, verifying Cats don't get rulership.
        # Clearing 2 (Mouse) adjacent to 6 (Fox).
        c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        c6 = Clearing.objects.get(game=self.game, clearing_number=6)

        # Place 1 Cat warrior in 2 and 6
        WarriorFactory(player=self.player_cats, clearing=c2)
        WarriorFactory(player=self.player_cats, clearing=c6)

        # Place 1 WA warrior in 2 and 6. 
        # Clean up existing warriors first (Cats start with warriors everywhere)
        Warrior.objects.filter(clearing=c2).delete()
        Warrior.objects.filter(clearing=c6).delete()
        
        # 1 vs 1. Tied. No one rules (Birds not involved).
        WarriorFactory(player=self.player_cats, clearing=c2)
        WarriorFactory(player=self.player_cats, clearing=c6)
        WarriorFactory(player=self.player_wa, clearing=c2)
        WarriorFactory(player=self.player_wa, clearing=c6)

        # Cats try to move 2 -> 6.
        # Cats do not rule 2 (Tied).
        # Cats do not rule 6 (Tied).
        with self.assertRaisesRegex(ValueError, "does not control either"):
            move_warriors(self.player_cats, c2, c6, 1)

    def test_move_insufficient_warriors(self):
        # Cats have 1 in 1. Try to move 2.
        # Ensure exact count
        Warrior.objects.filter(player=self.player_cats, clearing=self.c1).delete()
        WarriorFactory(player=self.player_cats, clearing=self.c1)

        with self.assertRaisesRegex(ValueError, "not enough warriors"):
            move_warriors(self.player_cats, self.c1, self.c5, 2)

    def test_move_zero_warriors(self):
        # Provide warriors but try to move 0
        WarriorFactory(player=self.player_cats, clearing=self.c1)
        
        with self.assertRaisesRegex(ValueError, "Cannot move 0"):
            move_warriors(self.player_cats, self.c1, self.c5, 0)

    def test_move_all(self):
        # Move all warriors from a clearing
        Warrior.objects.filter(player=self.player_cats, clearing=self.c1).delete()
        WarriorFactory(player=self.player_cats, clearing=self.c1)
        WarriorFactory(player=self.player_cats, clearing=self.c1)
        
        initial_c5 = Warrior.objects.filter(player=self.player_cats, clearing=self.c5).count()
        
        move_warriors(self.player_cats, self.c1, self.c5, 2)
        
        self.assertEqual(Warrior.objects.filter(player=self.player_cats, clearing=self.c1).count(), 0)
        self.assertEqual(Warrior.objects.filter(player=self.player_cats, clearing=self.c5).count(), initial_c5 + 2)
