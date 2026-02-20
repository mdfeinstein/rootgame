from django.test import TestCase
from game.models.game_models import Faction, Clearing, Card, HandEntry, Suit, Game, Warrior
from game.models.dominance import DominanceSupplyEntry, ActiveDominanceEntry
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, WarriorFactory
from game.transactions.dominance import swap_dominance, activate_dominance, check_dominance_victory
from game.game_data.cards.exiles_and_partisans import CardsEP

class DominanceTests(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE])
        self.cats = self.game.players.get(faction=Faction.CATS)
        self.birds = self.game.players.get(faction=Faction.BIRDS)
        
        # Ensure Cats turn
        # The GameSetupWithFactionsFactory already creates a turn for the first player (Cats)
        self.game.current_turn = 0
        self.game.save()
        
        # Transition Cats to Daylight
        from game.models.cats.turn import CatTurn, CatBirdsong
        turn = CatTurn.objects.filter(player=self.cats).last()
        turn.birdsong.step = CatBirdsong.CatBirdsongSteps.COMPLETED
        turn.birdsong.save()
        
        # Setup clearings for victory check
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1) # Fox (Red)
        self.c6 = Clearing.objects.get(game=self.game, clearing_number=6) # Fox (Red)
        self.c8 = Clearing.objects.get(game=self.game, clearing_number=8) # Fox (Red)
        
        # Clear warriors
        Warrior.objects.all().delete()

    def test_dominance_swap(self):
        # Daylight is now current phase
        
        # Setup: Dominance card in supply
        fox_dom_card = CardFactory(game=self.game, card_type=CardsEP.DOMINANCE_RED.name)
        dom_entry = DominanceSupplyEntry.objects.create(game=self.game, card=fox_dom_card)
        
        # Player has a Fox card in hand
        # Card suit is determined by card_type in Card model property
        spending_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        hand_entry = HandEntry.objects.create(player=self.cats, card=spending_card)
        
        # Swap
        swap_dominance(self.cats, hand_entry, dom_entry)
        
        # Verify
        self.assertTrue(HandEntry.objects.filter(player=self.cats, card=fox_dom_card).exists())
        self.assertFalse(DominanceSupplyEntry.objects.filter(game=self.game, card=fox_dom_card).exists())
        self.assertFalse(HandEntry.objects.filter(player=self.cats, card=spending_card).exists())

    def test_dominance_activation(self):
        # Setup: Player has 10 points
        self.cats.score = 10
        self.cats.save()
        
        dom_card = CardFactory(game=self.game, card_type=CardsEP.DOMINANCE_RED.name)
        hand_entry = HandEntry.objects.create(player=self.cats, card=dom_card)
        
        # Activate
        activate_dominance(self.cats, hand_entry)
        
        # Verify
        self.assertTrue(ActiveDominanceEntry.objects.filter(player=self.cats, card=dom_card).exists())
        self.assertFalse(HandEntry.objects.filter(player=self.cats, card=dom_card).exists())

    def test_dominance_victory_logic(self):
        # Setup: Cats have Red (Fox) dominance
        dom_card = CardFactory(game=self.game, card_type=CardsEP.DOMINANCE_RED.name)
        ActiveDominanceEntry.objects.create(player=self.cats, card=dom_card)
        
        # Rule 3 Fox clearings (1, 6, 8)
        for c in [self.c1, self.c6, self.c8]:
            WarriorFactory.create_batch(5, player=self.cats, clearing=c)
            
        # Trigger check
        check_dominance_victory(self.cats)
        
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, Game.GameStatus.COMPLETED)

    def test_bird_dominance_victory_logic(self):
        # Setup: Birds have Bird (Wild) dominance
        dom_card = CardFactory(game=self.game, card_type=CardsEP.DOMINANCE_WILD.name)
        ActiveDominanceEntry.objects.create(player=self.birds, card=dom_card)
        
        # Rule 2 opposite corners: 1 and 3
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        c3 = Clearing.objects.get(game=self.game, clearing_number=3)
        
        WarriorFactory.create_batch(5, player=self.birds, clearing=c1)
        WarriorFactory.create_batch(5, player=self.birds, clearing=c3)
        
        # Trigger check
        check_dominance_victory(self.birds)
        
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, Game.GameStatus.COMPLETED)
