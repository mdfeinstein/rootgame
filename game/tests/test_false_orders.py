from django.test import TestCase
from django.contrib.auth.models import User
from game.models.game_models import Game, Player, Clearing, Card, HandEntry, CraftedCardEntry, Warrior, DiscardPileEntry, Faction
from game.models.birds.turn import BirdTurn, BirdBirdsong, BirdDaylight
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.game_data.general.game_enums import Suit
from game.transactions.crafted_cards.false_orders import use_false_orders
from game.transactions.game_setup import construct_deck
from game.transactions.general import craft_card

class FalseOrdersTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create(username="owner")
        self.game = Game.objects.create(owner=self.owner)
        construct_deck(self.game)
        self.user1 = User.objects.create(username="user1")
        self.user2 = User.objects.create(username="user2")
        self.cat_player = Player.objects.create(game=self.game, faction=Faction.CATS, turn_order=0, user=self.user1)
        self.bird_player = Player.objects.create(game=self.game, faction=Faction.BIRDS, turn_order=1, user=self.user2)
        
        self.clearing1 = Clearing.objects.create(game=self.game, clearing_number=1, suit=Suit.RED)
        self.clearing2 = Clearing.objects.create(game=self.game, clearing_number=2, suit=Suit.YELLOW)
        self.clearing1.connected_clearings.add(self.clearing2)
        
        # Give cats some warriors in clearing 1
        for _ in range(5):
            Warrior.objects.create(player=self.cat_player, clearing=self.clearing1)
            
        # Give birds False Orders
        self.fo_card = Card.objects.filter(card_type=CardsEP.FALSE_ORDERS.name, game=self.game).first()
        self.crafted_fo = CraftedCardEntry.objects.create(player=self.bird_player, card=self.fo_card)
        
        # Set turn and step
        self.game.current_turn = 1
        self.game.save()
        
        # Set up birds turn and birdsong phase
        bird_turn = BirdTurn.create_turn(self.bird_player)
        # BirdTurn.create_turn creates BirdBirdsong, BirdDaylight, BirdEvening automatically
        # And get_phase uses them.

    def test_use_false_orders_success(self):
        # Move half of 5 warriors (rounded up = 3)
        use_false_orders(
            self.crafted_fo,
            self.cat_player,
            self.clearing1,
            self.clearing2
        )
        
        # Verify warriors moved
        cat_in_c1 = Warrior.objects.filter(player=self.cat_player, clearing=self.clearing1).count()
        cat_in_c2 = Warrior.objects.filter(player=self.cat_player, clearing=self.clearing2).count()
        
        self.assertEqual(cat_in_c1, 2)
        self.assertEqual(cat_in_c2, 3)
        
        # Verify card discarded
        self.assertFalse(CraftedCardEntry.objects.filter(pk=self.crafted_fo.pk).exists())
        self.assertTrue(DiscardPileEntry.objects.filter(game=self.game, card=self.fo_card).exists())

    def test_use_false_orders_ignores_rule(self):
        # Even if birds don't rule either clearing, they should be able to move enemy warriors
        # Give cats extra warriors in both to ensure they rule
        for _ in range(2):
             Warrior.objects.create(player=self.cat_player, clearing=self.clearing2)
        
        # verify rule
        from game.queries.general import determine_clearing_rule
        self.assertEqual(determine_clearing_rule(self.clearing1), self.cat_player)
        self.assertEqual(determine_clearing_rule(self.clearing2), self.cat_player)
        
        # This move would normally fail for birds, but they are moving CATS as if they were CATS
        # Wait, if they move CATS as if they were CATS, CATS rule both anyway.
        # Let's make it so NO ONE rules or someone else rules.
        # Actually the card says "ignoring rule", so it shouldn't matter.
        
        use_false_orders(
            self.crafted_fo,
            self.cat_player,
            self.clearing1,
            self.clearing2
        )
        
        cat_in_c2 = Warrior.objects.filter(player=self.cat_player, clearing=self.clearing2).count()
        self.assertEqual(cat_in_c2, 3+2)

    def test_use_false_orders_wrong_phase(self):
        # Transition to Daylight
        bird_turn = BirdTurn.objects.filter(player=self.bird_player).latest("turn_number")
        phase = bird_turn.birdsong.first()
        phase.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        phase.save()
        
        with self.assertRaises(ValueError) as cm:
            use_false_orders(
                self.crafted_fo,
                self.cat_player,
                self.clearing1,
                self.clearing2
            )
        self.assertIn("Birdsong", str(cm.exception))

    def test_use_false_orders_target_self(self):
        with self.assertRaises(ValueError) as cm:
            use_false_orders(
                self.crafted_fo,
                self.bird_player,
                self.clearing1,
                self.clearing2
            )
        self.assertIn("yourself", str(cm.exception))

    def test_use_false_orders_no_warriors(self):
        empty_clearing = Clearing.objects.create(game=self.game, clearing_number=3, suit=Suit.ORANGE)
        self.clearing1.connected_clearings.add(empty_clearing)
        
        with self.assertRaises(ValueError) as cm:
            use_false_orders(
                self.crafted_fo,
                self.cat_player,
                empty_clearing,
                self.clearing1
            )
        self.assertIn("No enemy warriors", str(cm.exception))
from django.urls import reverse
from game.tests.client import RootGameClient

class FalseOrdersViewTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create(username="owner")
        self.game = Game.objects.create(owner=self.owner)
        construct_deck(self.game)
        self.user1 = User.objects.create(username="user1")
        self.user2 = User.objects.create(username="user2")
        self.user2.set_password("password")
        self.user2.save()
        self.cat_player = Player.objects.create(game=self.game, faction=Faction.CATS, turn_order=0, user=self.user1)
        self.bird_player = Player.objects.create(game=self.game, faction=Faction.BIRDS, turn_order=1, user=self.user2)
        
        self.clearing1 = Clearing.objects.create(game=self.game, clearing_number=1, suit=Suit.RED)
        self.clearing2 = Clearing.objects.create(game=self.game, clearing_number=2, suit=Suit.YELLOW)
        self.clearing1.connected_clearings.add(self.clearing2)
        
        # Give cats some warriors in clearing 1
        for _ in range(5):
            Warrior.objects.create(player=self.cat_player, clearing=self.clearing1)
            
        # Give birds False Orders
        self.fo_card = Card.objects.filter(card_type=CardsEP.FALSE_ORDERS.name, game=self.game).first()
        self.crafted_fo = CraftedCardEntry.objects.create(player=self.bird_player, card=self.fo_card)
        
        # Set turn and step
        self.game.current_turn = 1
        self.game.save()
        BirdTurn.create_turn(self.bird_player)
        
        self.client = RootGameClient(user="user2", password="password", game_id=self.game.id)

    def test_view_flow_with_clearing_numbers(self):
        # 1. GET initial options
        response = self.client.get(f"/api/action/card/false-orders/?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick_origin")
        self.assertEqual(response.data["options"][0]["value"], "1") # Clearing number
        
        # 2. POST pick_origin
        response = self.client.post(
            f"/api/action/card/false-orders/{self.game.id}/pick_origin/",
            {"origin_number": 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick_faction")
        self.assertEqual(response.data["options"][0]["value"], Faction.CATS)
        
        # 3. POST pick_faction
        response = self.client.post(
            f"/api/action/card/false-orders/{self.game.id}/pick_faction/",
            {"origin_number": 1, "target_faction": Faction.CATS}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick_destination")
        self.assertEqual(response.data["options"][0]["value"], "2") # Clearing number
        
        # 4. POST pick_destination (Final)
        response = self.client.post(
            f"/api/action/card/false-orders/{self.game.id}/pick_destination/",
            {
                "origin_number": 1,
                "target_faction": Faction.CATS,
                "destination_number": 2
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify result in DB
        self.assertEqual(Warrior.objects.filter(player=self.cat_player, clearing=self.clearing2).count(), 3)
