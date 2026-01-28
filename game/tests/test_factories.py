from django.test import TestCase
from game.tests.my_factories import GameSetupFactory, BirdTurnFactory
from game.models.game_models import Faction, Game

class TestFactories(TestCase):
    def test_game_setup_factory(self):
        game = GameSetupFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.assertEqual(game.players.count(), 2)
        self.assertEqual(game.status, Game.GameStatus.STARTED)
        
        cats = game.players.get(faction=Faction.CATS)
        birds = game.players.get(faction=Faction.BIRDS)
        
        self.assertEqual(cats.turn_order, 0)
        self.assertEqual(birds.turn_order, 1)
        
        # Check components
        self.assertTrue(cats.warrior_supply_entries.exists())
        self.assertTrue(birds.warrior_supply_entries.exists())
        
    def test_bird_turn_factory(self):
        game = GameSetupFactory(factions=[Faction.BIRDS])
        player = game.players.first()
        turn = BirdTurnFactory(player=player)
        self.assertIsNotNone(turn.birdsong)
        self.assertIsNotNone(turn.daylight)
        self.assertIsNotNone(turn.evening)

    def test_game_setup_with_factions_factory(self):
        # game = GameSetupFactory(factions=[Faction.CATS, Faction.BIRDS])
        from game.tests.my_factories import GameSetupWithFactionsFactory
        game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE], generate_fixture=True)
        
        # Verify Cats Setup
        cats = game.players.get(faction=Faction.CATS)
        # Check keep in clearing 1
        from game.models import Token
        self.assertTrue(Token.objects.filter(player=cats, clearing__clearing_number=1).exists()) # Token set for Keep?
        # Ideally check for "Keep" token type specifically if possible
        
        # Check buildings
        from game.models import Building, Warrior
        self.assertTrue(Building.objects.filter(player=cats, building_slot__clearing__clearing_number=1).exists())
        self.assertTrue(Building.objects.filter(player=cats, building_slot__clearing__clearing_number=5).exists())
        self.assertTrue(Building.objects.filter(player=cats, building_slot__clearing__clearing_number=9).exists())
        
        # Verify Birds Setup
        birds = game.players.get(faction=Faction.BIRDS)
        # Check roost in 3 (opposite of 1)
        self.assertTrue(Building.objects.filter(player=birds, building_slot__clearing__clearing_number=3).exists())
        # Check Warriors count (6 starting warriors)
        self.assertEqual(Warrior.objects.filter(player=birds, clearing__clearing_number=3).count(), 6)
