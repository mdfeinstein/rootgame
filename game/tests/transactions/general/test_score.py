from django.test import TestCase
from game.models.game_models import Faction, Game
from game.models.dominance import ActiveDominanceEntry
from game.tests.my_factories import GameSetupFactory, CardFactory
from game.transactions.general import raise_score
from game.game_data.cards.exiles_and_partisans import CardsEP

class ScoreTests(TestCase):
    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.CATS])
        self.player = self.game.players.first()
        self.player.score = 0
        self.player.save()

    def test_raise_score(self):
        raise_score(self.player, 5)
        self.player.refresh_from_db()
        self.assertEqual(self.player.score, 5)

    def test_victory_condition(self):
        self.player.score = 29
        self.player.save()
        
        raise_score(self.player, 1)
        self.player.refresh_from_db()
        self.game.refresh_from_db()
        
        self.assertEqual(self.player.score, 30)
        self.assertEqual(self.game.status, Game.GameStatus.COMPLETED)

    def test_dominance_prevents_score_increase(self):
        # Create active dominance
        card = CardFactory(game=self.game, card_type=CardsEP.DOMINANCE_RED.name)
        ActiveDominanceEntry.objects.create(player=self.player, card=card)
        # self.player.active_dominance is a relation, so creating the object is enough.
        # Check model definition for active_dominance
        # It's likely a property or related field check.
        # general.raise_score check:
        # try: if player.active_dominance: ... except ActiveDominanceEntry.DoesNotExist: ...
        # If it's a OneToOne or Reverse ForeignKey, `player.active_dominance` access might raise DoesNotExist if not present.
        
        # raise_score logic handles the check.
        
        raise_score(self.player, 5)
        self.player.refresh_from_db()
        self.assertEqual(self.player.score, 0) # Should not increase
