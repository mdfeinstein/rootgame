from django.test import TestCase
from game.models.game_models import Faction, Card, DeckEntry, DiscardPileEntry, HandEntry
from game.models.dominance import DominanceSupplyEntry
from game.tests.my_factories import GameSetupFactory, CardFactory, PlayerFactory
from game.transactions.general import draw_card_from_deck_to_hand, discard_card_from_hand
from game.game_data.cards.exiles_and_partisans import CardsEP

class DeckTests(TestCase):
    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.CATS])
        self.player = self.game.players.first()
        # Clear existing deck/hand/discard from setup
        DeckEntry.objects.filter(game=self.game).delete()
        HandEntry.objects.filter(player=self.player).delete()
        DiscardPileEntry.objects.filter(game=self.game).delete()
        DominanceSupplyEntry.objects.filter(game=self.game).delete()

    def test_draw_card_from_deck_to_hand(self):
        # Setup: Deck has 1 card
        card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        DeckEntry.objects.create(game=self.game, card=card, spot=0)
        
        draw_card_from_deck_to_hand(self.player)
        
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), 1)
        self.assertEqual(DeckEntry.objects.filter(game=self.game).count(), 0)

    def test_reshuffle(self):
        # Setup: Deck empty. Discard has 2 cards.
        card1 = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        card2 = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_YELLOW.name)
        
        DiscardPileEntry.objects.create(game=self.game, card=card1, spot=0)
        DiscardPileEntry.objects.create(game=self.game, card=card2, spot=1)
        
        # Draw triggers reshuffle
        draw_card_from_deck_to_hand(self.player)
        
        # 2 cards total. 1 in hand. 1 in deck. 0 in discard.
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), 1)
        self.assertEqual(DeckEntry.objects.filter(game=self.game).count(), 1)
        self.assertEqual(DiscardPileEntry.objects.filter(game=self.game).count(), 0)

    def test_discard_card_from_hand(self):
        # Setup: Hand has 1 normal card
        card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        hand_entry = HandEntry.objects.create(player=self.player, card=card)
        
        discard_card_from_hand(self.player, hand_entry)
        
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), 0)
        self.assertEqual(DiscardPileEntry.objects.filter(game=self.game).count(), 1)
        self.assertEqual(DiscardPileEntry.objects.first().card, card)

    def test_discard_dominance(self):
        # Setup: Hand has 1 dominance card
        card = CardFactory(game=self.game, card_type=CardsEP.DOMINANCE_RED.name)
        hand_entry = HandEntry.objects.create(player=self.player, card=card)
        
        discard_card_from_hand(self.player, hand_entry)
        
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), 0)
        # Should NOT be in discard pile
        self.assertEqual(DiscardPileEntry.objects.filter(game=self.game).count(), 0)
        # Should be in Dominance Supply
        self.assertTrue(DominanceSupplyEntry.objects.filter(game=self.game, card=card).exists())
