from django.test import TestCase
from django.contrib.auth.models import User
from game.models.game_models import Game, Player, Faction, Card, CraftedCardEntry, HandEntry
from game.models.birds.turn import BirdTurn, BirdBirdsong
from game.models.events.crafted_cards import SwapMeetEvent
from game.models.events.setup import GameSimpleSetup
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.game_setup import construct_deck
from game.transactions.crafted_cards.swap_meet import swap_meet_take_card, swap_meet_give_card
from game.tests.client import RootGameClient

class SwapMeetTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create(username="owner")
        self.game = Game.objects.create(owner=self.owner)
        construct_deck(self.game)
        GameSimpleSetup.objects.create(game=self.game, status=GameSimpleSetup.GameSetupStatus.ALL_SETUP_COMPLETED)
        
        # Player 1 (Birds)
        self.user1 = User.objects.create(username="user1")
        self.user1.set_password("password")
        self.user1.save()
        self.player1 = Player.objects.create(game=self.game, faction=Faction.BIRDS, turn_order=0, user=self.user1)
        
        # Player 2 (Cats)
        self.user2 = User.objects.create(username="user2")
        self.user2.set_password("password")
        self.user2.save()
        self.player2 = Player.objects.create(game=self.game, faction=Faction.CATS, turn_order=1, user=self.user2)
        
        # Crafted Swap Meet for Player 1
        self.sm_card = Card.objects.filter(card_type=CardsEP.SWAP_MEET.name, game=self.game).first()
        self.crafted_sm = CraftedCardEntry.objects.create(player=self.player1, card=self.sm_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Set turn and phase
        self.game.current_turn = self.player1.turn_order
        self.game.save()
        self.turn = BirdTurn.create_turn(self.player1)
        birdsong = BirdBirdsong.objects.get(turn=self.turn)
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE
        birdsong.save()
        
        # Give Player 2 a card
        self.target_card = Card.objects.filter(game=self.game).exclude(id=self.sm_card.id).first()
        self.h2 = HandEntry.objects.create(player=self.player2, card=self.target_card)
        
        # Give Player 1 a card to give back
        self.give_card = Card.objects.filter(game=self.game).exclude(id__in=[self.sm_card.id, self.target_card.id]).first()
        self.h1 = HandEntry.objects.create(player=self.player1, card=self.give_card)
        
        self.client = RootGameClient(user="user1", password="password", game_id=self.game.id)

    def test_transaction_flow(self):
        # 1. Take card
        taken_card = swap_meet_take_card(self.player1, self.player2)
        self.assertEqual(taken_card, self.target_card)
        self.assertEqual(HandEntry.objects.filter(player=self.player1).count(), 2)
        self.assertEqual(HandEntry.objects.filter(player=self.player2).count(), 0)
        
        event = SwapMeetEvent.objects.get(taking_player=self.player1)
        self.assertFalse(event.event.is_resolved)
        
        # 2. Give card back
        swap_meet_give_card(event, CardsEP[self.give_card.card_type])
        self.assertEqual(HandEntry.objects.filter(player=self.player1).count(), 1)
        self.assertEqual(HandEntry.objects.filter(player=self.player2).count(), 1)
        self.assertEqual(HandEntry.objects.get(player=self.player2).card, self.give_card)
        self.assertTrue(event.event.is_resolved)

    def test_view_flow(self):
        # 1. Pick opponent (Take Card)
        # Swap Meet is a manual action, so we HIT the endpoint first
        response = self.client.get(f"/api/action/card/swap-meet-take/?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-opponent")
        
        # Use submit_action helper
        # RootGameClient.submit_action expects a dict where keys are payload "type"
        # In SwapMeetPickOpponentView, type is "select"
        self.client.step = response.json()
        self.client.base_route = f"/api/action/card/swap-meet-take/"
        
        response = self.client.submit_action({"select": Faction.CATS})
        self.assertEqual(response.status_code, 200)
        
        # Verify transaction check
        self.assertEqual(HandEntry.objects.filter(player=self.player1).count(), 2)
        
        # 2. Pick card to give (Give Card)
        # This is an event-driven action, so it should be returned by get_action()
        response = self.client.get_action()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.step["name"], "pick-card-to-give")
        
        # In SwapMeetGiveCardView, type is "card"
        response = self.client.submit_action({"card": self.give_card.card_type})
        self.assertEqual(response.status_code, 200)
        
        # Verify final state
        self.assertEqual(HandEntry.objects.filter(player=self.player2).count(), 1)
        self.assertEqual(HandEntry.objects.get(player=self.player2).card, self.give_card)
        
        # Verify event resolved
        event = SwapMeetEvent.objects.get(taking_player=self.player1)
        self.assertTrue(event.event.is_resolved)
