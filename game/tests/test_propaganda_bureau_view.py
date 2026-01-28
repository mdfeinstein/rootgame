from django.test import TestCase
from django.contrib.auth.models import User
from game.models.game_models import Game, Player, Faction, Card, HandEntry, Clearing, Suit, Warrior
from game.models.birds.turn import BirdTurn
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.game_setup import construct_deck
from game.tests.client import RootGameClient

class PropagandaBureauViewTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create(username="owner")
        self.game = Game.objects.create(owner=self.owner)
        construct_deck(self.game)
        self.user1 = User.objects.create(username="user1")
        self.user1.set_password("password")
        self.user1.save()
        
        # Player 1 (Birds) has Propaganda Bureau crafted and a card to spend
        self.player = Player.objects.create(game=self.game, faction=Faction.BIRDS, turn_order=0, user=self.user1)
        self.pb_card = Card.objects.filter(card_type=CardsEP.PROPAGANDA_BUREAU.name, game=self.game).first()
        from game.models.game_models import CraftedCardEntry
        self.crafted_pb = CraftedCardEntry.objects.create(player=self.player, card=self.pb_card)
        
        # Give player a FOX card to spend
        self.fox_card = Card.objects.filter(suit=Suit.RED, game=self.game).exclude(pk=self.pb_card.pk).first()
        HandEntry.objects.create(player=self.player, card=self.fox_card)
        
        # Board Setup: Target clearing (Fox) with an enemy warrior
        self.clearing_fox = Clearing.objects.create(game=self.game, clearing_number=1, suit=Suit.RED)
        self.cat_user = User.objects.create(username="cat_user")
        self.cat_player = Player.objects.create(game=self.game, faction=Faction.CATS, turn_order=1, user=self.cat_user)
        Warrior.objects.create(player=self.cat_player, clearing=self.clearing_fox)
        
        # Player warrior in supply
        self.bird_warrior = Warrior.objects.create(player=self.player, clearing=None)
        
        # Set turn and phase (Birds Daylight)
        self.game.current_turn = self.player.turn_order
        self.game.save()
        turn = BirdTurn.create_turn(self.player)
        from game.models.birds.turn import BirdBirdsong, BirdDaylight
        # Must complete birdsong for is_phase("Daylight") to work if it checks previous phase
        # Actually is_phase in birds just checks if birdsong is completed and evening not started.
        BirdBirdsong.objects.filter(turn=turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=turn).update(step=BirdDaylight.BirdDaylightSteps.CRAFTING)
        
        self.client = RootGameClient(user="user1", password="password", game_id=self.game.id)

    def test_view_flow_with_clearing_numbers(self):
        # 1. GET initial options (cards in hand)
        response = self.client.get(f"/api/action/card/propaganda-bureau/?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick_card")
        self.assertEqual(response.data["options"][0]["value"], self.fox_card.card_type)
        
        # 2. POST pick_card
        response = self.client.post(
            f"/api/action/card/propaganda-bureau/{self.game.id}/pick_card/",
            {"card_name": self.fox_card.card_type}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick_clearing")
        self.assertEqual(response.data["options"][0]["value"], "1") # clearing_number
        
        # 3. POST pick_clearing
        response = self.client.post(
            f"/api/action/card/propaganda-bureau/{self.game.id}/pick_clearing/",
            {"card_name": self.fox_card.card_type, "clearing_number": 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick_opponent")
        self.assertEqual(response.data["options"][0]["value"], Faction.CATS)
        
        # 4. POST pick_opponent (Final)
        response = self.client.post(
            f"/api/action/card/propaganda-bureau/{self.game.id}/pick_opponent/",
            {
                "card_name": self.fox_card.card_type,
                "clearing_number": 1,
                "target_faction": Faction.CATS
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify result in DB
        self.bird_warrior.refresh_from_db()
        self.assertEqual(self.bird_warrior.clearing, self.clearing_fox)
        self.assertEqual(Warrior.objects.filter(player=self.cat_player, clearing=self.clearing_fox).count(), 0)
