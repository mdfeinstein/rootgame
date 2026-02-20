from django.test import TestCase
from game.models.game_models import Faction, CraftedCardEntry
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory
from game.transactions.general import next_players_turn
from game.game_data.cards.exiles_and_partisans import CardsEP

class TurnTests(TestCase):
    def setUp(self):
        # 2 Players with complete setup
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.player_cats = self.game.players.get(faction=Faction.CATS)
        self.player_birds = self.game.players.get(faction=Faction.BIRDS)
        
        # Ensure turn orders are correct
        self.assertEqual(self.player_cats.turn_order, 0)
        self.assertEqual(self.player_birds.turn_order, 1)
        
        self.game.current_turn = 0
        self.game.save()

    def test_next_players_turn_cycle(self):
        next_players_turn(self.game)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, 1)

        next_players_turn(self.game)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, 0)

    def test_crafted_card_reset(self):
        # Give Cats a used crafted card
        card_cats = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name)
        crafted_cats = CraftedCardEntryFactory(player=self.player_cats, card=card_cats, used=CraftedCardEntry.UsedChoice.USED)
        
        # Give Birds a used crafted card
        card_birds = CardFactory(game=self.game, card_type=CardsEP.INFORMANTS.name)
        crafted_birds = CraftedCardEntryFactory(player=self.player_birds, card=card_birds, used=CraftedCardEntry.UsedChoice.USED)
        
        # Move turn from Cats to Birds
        next_players_turn(self.game)
        
        # Birds (new player) card should be reset
        crafted_birds.refresh_from_db()
        self.assertEqual(crafted_birds.used, CraftedCardEntry.UsedChoice.UNUSED)
        
        # Cats (old player) card should remain USED
        crafted_cats.refresh_from_db()
        self.assertEqual(crafted_cats.used, CraftedCardEntry.UsedChoice.USED)
