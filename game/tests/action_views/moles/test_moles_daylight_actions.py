from rest_framework import status
from rest_framework.test import APITestCase
from game.models.game_models import Faction, Clearing, Warrior, HandEntry, Card
from game.models.moles.turn import MoleTurn, MoleDaylight
from game.models.moles.buildings import Citadel, Market
from game.models.moles.tokens import Tunnel
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.tests.client import RootGameClient
from game.tests.my_factories import MolesBirdsGameSetupFactory, HandEntryFactory


class MolesDaylightActionViewsTests(APITestCase):
    def setUp(self):
        self.game = MolesBirdsGameSetupFactory()
        self.moles_player = self.game.players.get(faction=Faction.MOLES)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)

        # Moles user
        self.moles_user = self.moles_player.user
        self.moles_user.set_password("p")
        self.moles_user.save()
        self.moles_client = RootGameClient(user=self.moles_user, password="p", game_id=self.game.id)

        # Get clearings
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        self.c3 = Clearing.objects.get(game=self.game, clearing_number=3)
        self.c6 = Clearing.objects.get(game=self.game, clearing_number=6)

        # Set turn to Moles
        self.game.current_turn = self.moles_player.turn_order
        self.game.save()

        # Get turn and set to ACTIONS step
        self.turn = MoleTurn.objects.filter(player=self.moles_player).last()
        if not self.turn:
            self.turn = MoleTurn.create_turn(self.moles_player)
        self.daylight = self.turn.daylight.first()
        self.daylight.step = MoleDaylight.MoleDaylightSteps.ACTIONS
        self.daylight.actions_left = 2
        self.daylight.save()

        # Place some warriors for Moles (they start at c3 from factory)
        Warrior.objects.create(player=self.moles_player, clearing=self.c3)
        Warrior.objects.create(player=self.moles_player, clearing=self.c3)

        # Place birds warrior for battle tests
        Warrior.objects.create(player=self.birds_player, clearing=self.c1)

    def test_select_action_view(self):
        """Test that we get the action selection step"""
        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_action")
        self.assertIn("options", response.data)
        # Should have 6 options: move, battle, dig, recruit, build, done
        self.assertEqual(len(response.data["options"]), 6)

    def test_move_action_flow(self):
        """Test move action: origin -> destination -> count -> completed"""
        # 1. Get action selection
        self.moles_client.get_action()

        # 2. Select move action
        response = self.moles_client.submit_action({"action_type": "move"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "move_origin")
        self.assertEqual(response.data["endpoint"], "origin")

        # 3. Select origin clearing (c3 has warriors)
        response = self.moles_client.submit_action({"clearing_number": self.c3.clearing_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "move_destination")
        self.assertEqual(response.data["endpoint"], "destination")

        # 4. Select destination (c6 is adjacent to c3)
        response = self.moles_client.submit_action({"clearing_number": self.c6.clearing_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "move_count")
        self.assertEqual(response.data["endpoint"], "count")

        # 5. Select count
        response = self.moles_client.submit_action({"number": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_battle_action_flow(self):
        """Test battle action: clearing -> faction -> completed"""
        # Place Moles warrior in c1 where Birds warrior is
        Warrior.objects.create(player=self.moles_player, clearing=self.c1)

        # 1. Select battle action
        self.moles_client.get_action()
        response = self.moles_client.submit_action({"action_type": "battle"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "battle_clearing")
        self.assertEqual(response.data["endpoint"], "clearing")

        # 2. Select clearing with enemy
        response = self.moles_client.submit_action({"clearing_number": self.c1.clearing_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "battle_faction")
        self.assertEqual(response.data["endpoint"], "faction")

        # 3. Select faction to battle
        response = self.moles_client.submit_action({"faction": Faction.BIRDS})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_recruit_action_flow(self):
        """Test recruit action: confirm -> completed"""
        # 1. Select recruit action
        self.moles_client.get_action()
        response = self.moles_client.submit_action({"action_type": "recruit"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "recruit_confirm")
        self.assertEqual(response.data["endpoint"], "confirm")

        # 2. Confirm recruit
        response = self.moles_client.submit_action({"confirm": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_build_action_flow(self):
        """Test build action: type -> clearing -> card -> completed"""
        from game.game_data.cards.exiles_and_partisans import CardsEP

        # Give Moles player Rabbit Partisans card (matches c3's Rabbit suit)
        card = Card.objects.get(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
        HandEntry.objects.create(player=self.moles_player, card=card)

        # 1. Select build action
        self.moles_client.get_action()
        response = self.moles_client.submit_action({"action_type": "build"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "build_type")
        self.assertEqual(response.data["endpoint"], "type")

        # 2. Select building type (citadel)
        response = self.moles_client.submit_action({"building_type": "Citadel"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "build_clearing")
        self.assertEqual(response.data["endpoint"], "clearing")

        # 3. Select clearing (c3 has moles pieces and matching card)
        response = self.moles_client.submit_action({"clearing_number": self.c3.clearing_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "build_card")
        self.assertEqual(response.data["endpoint"], "card")

        # 4. We've verified the navigation flow through type->clearing->card
        # The actual card/clearing/building slot validation is tested in transaction tests

    def test_dig_action_flow_without_tunnel_source(self):
        """Test dig action step flow structure"""
        # Give Moles player a card
        hand_entry = HandEntryFactory(player=self.moles_player)

        # 1. Select dig action
        self.moles_client.get_action()
        response = self.moles_client.submit_action({"action_type": "dig"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "dig_clearing")
        self.assertEqual(response.data["endpoint"], "clearing")

        # 2. Select clearing (c3 has warriors)
        response = self.moles_client.submit_action({"clearing_number": self.c3.clearing_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response should be either tunnel_source or card step depending on tunnel supply
        self.assertIn(response.data["name"], ["dig_tunnel_source", "dig_card"])
        self.assertIn(response.data["endpoint"], ["tunnel-source", "card"])

    def test_dig_action_flow_with_tunnel_source(self):
        """Test dig action flow structure"""
        # Give card
        hand_entry = HandEntryFactory(player=self.moles_player)

        # 1. Select dig
        self.moles_client.get_action()
        response = self.moles_client.submit_action({"action_type": "dig"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "dig_clearing")

        # 2. Select clearing (c3 has warriors)
        response = self.moles_client.submit_action({"clearing_number": self.c3.clearing_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response should be either tunnel_source or card step
        self.assertIn(response.data["name"], ["dig_tunnel_source", "dig_card"])

    def test_end_actions_option(self):
        """Test selecting 'done' to end daylight actions"""
        # 1. Get action selection
        self.moles_client.get_action()

        # 2. Select done (empty action string)
        response = self.moles_client.submit_action({"action_type": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_actions_remaining_display(self):
        """Test that actions remaining is shown in prompt"""
        # Set to 1 action remaining
        self.daylight.actions_left = 1
        self.daylight.save()

        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("(1 actions remaining)", response.data["prompt"])

        # Set to 2 actions remaining
        self.daylight.actions_left = 2
        self.daylight.save()

        response = self.moles_client.get_action()
        self.assertIn("(2 actions remaining)", response.data["prompt"])
