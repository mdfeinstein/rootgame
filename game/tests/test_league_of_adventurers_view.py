from django.test import TestCase
from django.contrib.auth.models import User
from game.models.game_models import Game, Player, Faction, Card, CraftedItemEntry, Clearing, Suit, Warrior, CraftedCardEntry, BuildingSlot
from game.models.birds.turn import BirdTurn, BirdBirdsong, BirdDaylight
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.game_setup import construct_deck
from game.tests.client import RootGameClient

class LeagueOfAdventurersViewTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create(username="owner")
        self.game = Game.objects.create(owner=self.owner)
        from game.transactions.game_setup import construct_deck, create_craftable_item_supply
        construct_deck(self.game)
        create_craftable_item_supply(self.game)
        self.user1 = User.objects.create(username="user1")
        self.user1.set_password("password")
        self.user1.save()
        
        self.player = Player.objects.create(game=self.game, faction=Faction.BIRDS, turn_order=0, user=self.user1)
        self.lo_card = Card.objects.filter(card_type=CardsEP.LEAGUE_OF_ADVENTURERS.name, game=self.game).first()
        self.crafted_lo = CraftedCardEntry.objects.create(player=self.player, card=self.lo_card)
        
        # Give player an item to exhaust
        from game.models.game_models import Item
        boot = Item.objects.filter(item_type=Item.ItemTypes.BOOTS).first()
        self.crafted_item = CraftedItemEntry.objects.create(player=self.player, item=boot)
        
        # Board Setup
        self.clearing1 = Clearing.objects.create(game=self.game, clearing_number=1, suit=Suit.RED)
        self.clearing2 = Clearing.objects.create(game=self.game, clearing_number=2, suit=Suit.YELLOW)
        self.clearing1.connected_clearings.add(self.clearing2)
        
        # Player warriors in clearing 1
        Warrior.objects.create(player=self.player, clearing=self.clearing1)
        # Bird must rule origin or destination to move with League of Adventurers
        # Add a roost to clearing 1 to ensure rule
        from game.models.birds.buildings import BirdRoost
        slot = BuildingSlot.objects.create(clearing=self.clearing1, building_slot_number=0)
        BirdRoost.objects.create(player=self.player, building_slot=slot)
        
        # Enemy in clearing 1 for battle test
        self.cat_user = User.objects.create(username="cat_user")
        self.cat_player = Player.objects.create(game=self.game, faction=Faction.CATS, turn_order=1, user=self.cat_user)
        Warrior.objects.create(player=self.cat_player, clearing=self.clearing1)
        
        # Set turn and phase (Birds Daylight)
        self.game.current_turn = self.player.turn_order
        self.game.save()
        turn = BirdTurn.create_turn(self.player)
        BirdBirdsong.objects.filter(turn=turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=turn).update(step=BirdDaylight.BirdDaylightSteps.CRAFTING)
        
        self.client = RootGameClient(user="user1", password="password", game_id=self.game.id)

    def test_move_flow_with_clearing_numbers(self):
        # 1. GET initial options (items)
        response = self.client.get(f"/api/action/card/league-of-adventurers/?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-item")
        self.assertEqual(response.data["options"][0]["value"], str(self.crafted_item.id))
        
        # 2. POST pick-item
        response = self.client.post(
            f"/api/action/card/league-of-adventurers/{self.game.id}/pick-item/",
            {"item_id": self.crafted_item.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-action")
        
        # 3. POST pick-action (move)
        response = self.client.post(
            f"/api/action/card/league-of-adventurers/{self.game.id}/pick-action/",
            {"item_id": self.crafted_item.id, "action_type": "move"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-origin")
        self.assertEqual(response.data["options"][0]["value"], "1") # origin_number
        
        # 4. POST pick-origin
        response = self.client.post(
            f"/api/action/card/league-of-adventurers/{self.game.id}/pick-origin/",
            {"item_id": self.crafted_item.id, "action_type": "move", "origin_number": 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-destination")
        self.assertEqual(response.data["options"][0]["value"], "2") # destination_number
        
        # 5. POST pick-destination
        response = self.client.post(
            f"/api/action/card/league-of-adventurers/{self.game.id}/pick-destination/",
            {
                "item_id": self.crafted_item.id,
                "action_type": "move",
                "origin_number": 1,
                "destination_number": 2
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-count")
        
        # 6. POST pick-count (Final)
        response = self.client.post(
            f"/api/action/card/league-of-adventurers/{self.game.id}/pick-count/",
            {
                "item_id": self.crafted_item.id,
                "action_type": "move",
                "origin_number": 1,
                "destination_number": 2,
                "count": 1
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify result
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=self.clearing2).count(), 1)

    def test_battle_flow_with_clearing_numbers(self):
        # Continue from pick-action step
        # 3. POST pick-action (battle)
        response = self.client.post(
            f"/api/action/card/league-of-adventurers/{self.game.id}/pick-action/",
            {"item_id": self.crafted_item.id, "action_type": "battle"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-clearing")
        self.assertEqual(response.data["options"][0]["value"], "1") # clearing_number
        
        # 4. POST pick-clearing
        response = self.client.post(
            f"/api/action/card/league-of-adventurers/{self.game.id}/pick-clearing/",
            {"item_id": self.crafted_item.id, "action_type": "battle", "clearing_number": 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pick-opponent")
        self.assertEqual(response.data["options"][0]["value"], Faction.CATS)
        
        # 5. POST pick-opponent (Final)
        response = self.client.post(
            f"/api/action/card/league-of-adventurers/{self.game.id}/pick-opponent/",
            {
                "item_id": self.crafted_item.id,
                "action_type": "battle",
                "clearing_number": 1,
                "opponent_faction": Faction.CATS
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify battle started
        from game.models.events.battle import Battle
        self.assertTrue(Battle.objects.filter(clearing=self.clearing1, attacker=self.player.faction).exists())
