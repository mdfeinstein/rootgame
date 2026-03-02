from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, HandEntry, Player
from game.models.crows.tokens import PlotToken
from game.models.crows.exposure import ExposureRevealedCards, ExposureGuessedPlot
from game.models.events.event import Event, EventType
from game.models.events.battle import Battle
from game.models.cats.turn import CatTurn, CatEvening
from game.tests.my_factories import GameSetupFactory, CardFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.crows.exposure import can_attempt_exposure
from game.transactions.crows.exposure import guess_exposure
from game.transactions.battle import roll_dice

class CrowsExposureAndAgentsTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.CATS, Faction.CROWS])
        self.crows_player = self.game.players.get(faction=Faction.CROWS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        
        self.turn_cats = CatTurn.create_turn(self.cats_player)
        self.game.current_turn = self.cats_player.turn_order
        self.game.save()
        
        # Cats have a warrior in C1
        c_warrior = Warrior.objects.filter(player=self.cats_player).first()
        c_warrior.clearing = self.c1
        c_warrior.save()

        # Crows also have a warrior in C1
        cr_warrior = Warrior.objects.filter(player=self.crows_player).first()
        cr_warrior.clearing = self.c1
        cr_warrior.save()

        # Place a facedown plot token in C1
        self.token = PlotToken.objects.filter(player=self.crows_player, plot_type=PlotToken.PlotType.BOMB).first()
        self.token.clearing = self.c1
        self.token.is_facedown = True
        self.token.save()

        self.fox_card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name) # Fox suit
        self.mouse_card = CardFactory(game=self.game, card_type=CardsEP.MOUSE_PARTISANS.name) # Mouse suit
        # Let's make sure C1 is fox for testing suit matching
        self.c1.suit = "r"
        self.c1.save()

    def test_can_attempt_exposure_conditions(self):
        # Meets all conditions
        self.assertTrue(can_attempt_exposure(self.cats_player))

        # Crows cannot guess
        self.assertFalse(can_attempt_exposure(self.crows_player))

        # Not their turn
        self.game.current_turn = self.crows_player.turn_order
        self.game.save()
        self.assertFalse(can_attempt_exposure(self.cats_player))
        self.game.current_turn = self.cats_player.turn_order
        self.game.save()

        # Token is not facedown
        self.token.is_facedown = False
        self.token.save()
        self.assertFalse(can_attempt_exposure(self.cats_player))
        self.token.is_facedown = True
        self.token.save()

        # No pieces in clearing with facedown token
        c_warrior = Warrior.objects.filter(player=self.cats_player, clearing=self.c1).first()
        c_warrior.clearing = self.c2
        c_warrior.save()
        self.assertFalse(can_attempt_exposure(self.cats_player))
        c_warrior.clearing = self.c1
        c_warrior.save()

        # Already drawn in evening
        birdsong = self.turn_cats.birdsong
        birdsong.step = '3'
        birdsong.save()
        daylight = self.turn_cats.daylight
        daylight.step = '3'
        daylight.save()
        
        evening = self.turn_cats.evening
        evening.step = CatEvening.CatEveningSteps.DISCARDING
        evening.save()
        self.assertFalse(can_attempt_exposure(self.cats_player))

    def test_exposure_incorrect_guess(self):
        hand_entry = HandEntry.objects.create(player=self.cats_player, card=self.fox_card)
        
        guess_exposure(self.cats_player, self.c1, hand_entry, PlotToken.PlotType.SNARE)
        
        # Check card transferred to crows
        hand_entry.refresh_from_db()
        self.assertEqual(hand_entry.player, self.crows_player)
        
        # Check GuessedPlot log
        self.assertEqual(ExposureGuessedPlot.objects.count(), 1)
        log = ExposureGuessedPlot.objects.first()
        self.assertEqual(log.player, self.cats_player)
        self.assertEqual(log.guessed_plot_type, PlotToken.PlotType.SNARE)
        
        # Plot remained
        self.token.refresh_from_db()
        self.assertEqual(self.token.clearing, self.c1)

    def test_exposure_correct_guess(self):
        hand_entry = HandEntry.objects.create(player=self.cats_player, card=self.fox_card)
        starting_score = self.cats_player.score
        
        guess_exposure(self.cats_player, self.c1, hand_entry, PlotToken.PlotType.BOMB)
        
        # Card retained
        hand_entry.refresh_from_db()
        self.assertEqual(hand_entry.player, self.cats_player)
        
        # Revealed log created
        self.assertEqual(ExposureRevealedCards.objects.count(), 1)
        rev = ExposureRevealedCards.objects.first()
        self.assertEqual(rev.player, self.cats_player)
        self.assertEqual(rev.card, self.fox_card)
        
        # Token removed and 1 VP scored
        self.token.refresh_from_db()
        self.assertIsNone(self.token.clearing)
        self.cats_player.refresh_from_db()
        self.assertEqual(self.cats_player.score, starting_score + 1)

    def test_exposure_failures(self):
        hand_entry_fox = HandEntry.objects.create(player=self.cats_player, card=self.fox_card)
        hand_entry_mouse = HandEntry.objects.create(player=self.cats_player, card=self.mouse_card)
        
        # Wrong suit
        with self.assertRaisesMessage(ValueError, "Card suit does not match clearing suit"):
            guess_exposure(self.cats_player, self.c1, hand_entry_mouse, PlotToken.PlotType.BOMB)
            
        # Wrong player hand
        hand_entry_fox.player = self.crows_player
        hand_entry_fox.save()
        with self.assertRaisesMessage(ValueError, "Card is not in player's hand"):
            guess_exposure(self.cats_player, self.c1, hand_entry_fox, PlotToken.PlotType.BOMB)

    def test_embedded_agents_extra_hit_facedown(self):
        event = Event.objects.create(game=self.game, type=EventType.BATTLE)
        battle = Battle.objects.create(
            event=event,
            attacker=Faction.CATS,
            defender=Faction.CROWS,
            clearing=self.c1,
            step=Battle.BattleSteps.ROLL_DICE
        )
        
        # Provide exactly 2 warriors each to avoid wipeouts overriding hits
        Warrior.objects.filter(clearing=self.c1).update(clearing=None)
        
        cat_w1 = Warrior.objects.filter(player=self.cats_player)[0]
        cat_w2 = Warrior.objects.filter(player=self.cats_player)[1]
        cat_w1.clearing = self.c1; cat_w1.save()
        cat_w2.clearing = self.c1; cat_w2.save()
        
        cw1 = Warrior.objects.filter(player=self.crows_player)[0]
        cw2 = Warrior.objects.filter(player=self.crows_player)[1]
        cw1.clearing = self.c1; cw1.save()
        cw2.clearing = self.c1; cw2.save()
        
        # Roll dice (Mock random strictly not needed to observe effect, but we can compare before/after applied extra hits.
        # Actually roll_dice just adds +1 to attacker_hits_taken for Crows defender.
        from unittest.mock import patch
        with patch('game.transactions.battle.randint', side_effect=[1, 1]):
            roll_dice(self.game, battle)
            
        battle.refresh_from_db()
        # They both rolled 1. Base hits: attacker deals 1, defender deals 1.
        # Embedded agents adds +1 to attacker hits taken. So 2 total attacker hits taken.
        self.assertEqual(battle.defender_hits_taken, 1)
        self.assertEqual(battle.attacker_hits_taken, 2)

    def test_embedded_agents_no_hit_faceup(self):
        self.token.is_facedown = False
        self.token.save()
        
        event = Event.objects.create(game=self.game, type=EventType.BATTLE)
        battle = Battle.objects.create(
            event=event,
            attacker=Faction.CATS,
            defender=Faction.CROWS,
            clearing=self.c1,
            step=Battle.BattleSteps.ROLL_DICE
        )
        
        from unittest.mock import patch
        with patch('game.transactions.battle.randint', side_effect=[1, 1]):
            roll_dice(self.game, battle)
            
        battle.refresh_from_db()
        
        self.assertEqual(battle.defender_hits_taken, 1)
        self.assertEqual(battle.attacker_hits_taken, 1)
