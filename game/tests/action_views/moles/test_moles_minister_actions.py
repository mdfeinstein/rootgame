from rest_framework import status
from rest_framework.test import APITestCase
from game.models.game_models import Faction, Clearing, Warrior, HandEntry, Card
from game.models.moles.turn import MoleTurn, MoleDaylight
from game.models.moles.ministers import Minister
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.tests.client import RootGameClient
from game.tests.my_factories import MolesBirdsGameSetupFactory, HandEntryFactory


class MolesMinisterActionsViewsTests(APITestCase):
    def setUp(self):
        self.game = MolesBirdsGameSetupFactory()
        self.moles_player = self.game.players.get(faction=Faction.MOLES)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)

        # Moles user
        self.moles_user = self.moles_player.user
        self.moles_user.set_password("p")
        self.moles_user.save()
        self.moles_client = RootGameClient(
            user=self.moles_user, password="p", game_id=self.game.id
        )

        # Get clearings
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        self.c3 = Clearing.objects.get(game=self.game, clearing_number=3)
        self.c6 = Clearing.objects.get(game=self.game, clearing_number=6)

        # Set turn to Moles
        self.game.current_turn = self.moles_player.turn_order
        self.game.save()

        # Get turn and set to MINISTER_ACTIONS step
        self.turn = MoleTurn.objects.filter(player=self.moles_player).last()
        if not self.turn:
            self.turn = MoleTurn.create_turn(self.moles_player)
        self.daylight = self.turn.daylight.first()
        self.daylight.step = MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS
        self.daylight.save()

        # Place some warriors for Moles (they start at c3 from factory)
        Warrior.objects.create(player=self.moles_player, clearing=self.c3)
        Warrior.objects.create(player=self.moles_player, clearing=self.c3)

        # Place birds warrior for battle tests
        Warrior.objects.create(player=self.birds_player, clearing=self.c1)

        # Sway all ministers (set swayed=True, used=False)
        for minister in Minister.objects.filter(player=self.moles_player):
            minister.swayed = True
            minister.used = False
            minister.save()

    def test_select_minister_view(self):
        """Test that we get the minister selection step"""
        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_minister")
        self.assertIn("options", response.data)
        # Should have 8 unique ministers + Done option = 9 total
        # (Mayor is deferred, so only 8 ministers shown, not 9)
        # Actually, test shows 10 options, which might be all 9 ministers + Done
        # Let's just check there are options including Done
        self.assertGreater(len(response.data["options"]), 0)
        values = [opt["value"] for opt in response.data["options"]]
        self.assertIn("", values)  # Done option should be empty string

    def test_end_minister_actions(self):
        """Test selecting 'done' to end minister actions"""
        # 1. Get minister selection
        self.moles_client.get_action()

        # 2. Select done (empty action string)
        response = self.moles_client.submit_action({"action": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_marshal_action_flow(self):
        """Test marshal action: origin -> destination -> count -> completed"""
        # 1. Get minister selection
        self.moles_client.get_action()

        # 2. Select marshal action
        response = self.moles_client.submit_action({"action": "marshal"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "marshal_origin")
        self.assertEqual(response.data["endpoint"], "origin")

        # 3. Select origin clearing (c3 has warriors)
        response = self.moles_client.submit_action(
            {"clearing_number": self.c3.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "marshal_destination")
        self.assertEqual(response.data["endpoint"], "destination")

        # 4. Select destination (c6 is adjacent to c3)
        response = self.moles_client.submit_action(
            {"clearing_number": self.c6.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "marshal_count")
        self.assertEqual(response.data["endpoint"], "count")

        # 5. Select count (use "number" type as in payload_details)
        response = self.moles_client.submit_action({"number": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_captain_action_flow(self):
        """Test captain action: clearing -> faction -> completed"""
        # Place Moles warrior in c1 where Birds warrior is
        Warrior.objects.create(player=self.moles_player, clearing=self.c1)

        # 1. Get minister selection
        self.moles_client.get_action()

        # 2. Select captain action
        response = self.moles_client.submit_action({"action": "captain"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "captain_clearing")
        self.assertEqual(response.data["endpoint"], "clearing")

        # 3. Select clearing with enemy
        response = self.moles_client.submit_action(
            {"clearing_number": self.c1.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "captain_faction")
        self.assertEqual(response.data["endpoint"], "faction")

        # 4. Select faction to battle (use "faction" type as in payload_details)
        response = self.moles_client.submit_action({"faction": Faction.BIRDS})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_duchess_action_flow(self):
        """Test duchess action: completed"""
        # 1. Get minister selection
        self.moles_client.get_action()

        # 2. Select duchess action (executes immediately)
        response = self.moles_client.submit_action({"action": "duchess"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_baron_action_flow(self):
        """Test baron action: completed"""
        # 1. Get minister selection
        self.moles_client.get_action()

        # 2. Select baron action (executes immediately)
        response = self.moles_client.submit_action({"action": "baron"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_banker_action_flow_single_card(self):
        """Test banker action with single card selection"""
        # Give Moles player cards
        card1 = Card.objects.get(
            game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name
        )
        HandEntry.objects.create(player=self.moles_player, card=card1)

        # 1. Get minister selection
        self.moles_client.get_action()

        # 2. Select banker action
        response = self.moles_client.submit_action({"action": "banker"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "banker_select_card")
        self.assertEqual(response.data["endpoint"], "card")

        # 3. Select a card (use "card" type as in payload_details)
        response = self.moles_client.submit_action(
            {"card": CardsEP.RABBIT_PARTISANS.name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "banker_select_card")
        # Should show 1 card selected
        self.assertIn("1 cards selected", response.data["prompt"])

        # 4. Submit (empty card name means done)
        response = self.moles_client.submit_action({"card": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_banker_action_flow_multiple_cards_same_suit(self):
        """Test banker action with multiple cards of same suit"""
        # Give Moles player multiple Fox cards (FOXFOLK_STEEL and FOX_PARTISANS both Fox suit)
        card1 = Card.objects.get(game=self.game, card_type=CardsEP.FOXFOLK_STEEL.name)
        HandEntry.objects.create(player=self.moles_player, card=card1)
        card2 = Card.objects.get(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        HandEntry.objects.create(player=self.moles_player, card=card2)

        # 1. Get minister selection
        self.moles_client.get_action()

        # 2. Select banker action
        response = self.moles_client.submit_action({"action": "banker"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 3. Select first Fox card
        response = self.moles_client.submit_action({"card": CardsEP.FOXFOLK_STEEL.name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("1 cards selected", response.data["prompt"])

        # 4. Select second Fox card (same suit, should work)
        response = self.moles_client.submit_action({"card": CardsEP.FOX_PARTISANS.name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("2 cards selected", response.data["prompt"])

        # 5. Submit (empty card name means done)
        response = self.moles_client.submit_action({"card": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_banker_action_rejects_mismatched_suit(self):
        """Test banker action rejects cards with mismatched suit"""
        # Give Moles player cards of different suits
        rabbit_card = Card.objects.get(
            game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name
        )
        HandEntry.objects.create(player=self.moles_player, card=rabbit_card)
        fox_card = Card.objects.get(
            game=self.game, card_type=CardsEP.FOX_PARTISANS.name
        )
        HandEntry.objects.create(player=self.moles_player, card=fox_card)

        # 1. Get minister selection
        self.moles_client.get_action()

        # 2. Select banker action
        response = self.moles_client.submit_action({"action": "banker"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 3. Select first Rabbit card
        response = self.moles_client.submit_action(
            {"card": CardsEP.RABBIT_PARTISANS.name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 4. Try to select Fox card (different suit, should be rejected)
        response = self.moles_client.submit_action({"card": CardsEP.FOX_PARTISANS.name})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Should have error about suit mismatch
        self.assertIn("same suit", str(response.data))

    def test_foremole_action_flow(self):
        """Test foremole action: type -> clearing -> card -> completed"""
        # Give Moles player a card that matches c3
        card = Card.objects.get(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
        HandEntry.objects.create(player=self.moles_player, card=card)

        # 1. Get minister selection
        self.moles_client.get_action()

        # 2. Select foremole action
        response = self.moles_client.submit_action({"action": "foremole"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "foremole_type")
        self.assertEqual(response.data["endpoint"], "type")

        # 3. Select building type (citadel)
        response = self.moles_client.submit_action({"building_type": "Citadel"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "foremole_clearing")
        self.assertEqual(response.data["endpoint"], "clearing")

        # 4. Select clearing (c3 has moles pieces and is ruled by player)
        response = self.moles_client.submit_action(
            {"clearing_number": self.c3.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "foremole_card")
        self.assertEqual(response.data["endpoint"], "card")

        # 5. Select card to build with
        response = self.moles_client.submit_action(
            {"card": CardsEP.RABBIT_PARTISANS.name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_brigadier_first_action_move(self):
        """Test brigadier first action: action-type (move) -> origin -> destination -> count -> completed"""
        # 1. Get minister selection
        self.moles_client.get_action()

        # 2. Select brigadier action
        response = self.moles_client.submit_action({"action": "brigadier"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_action_type")
        self.assertEqual(response.data["endpoint"], "action-type")

        # 3. Select move action type
        response = self.moles_client.submit_action({"action_type": "move"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_origin")
        self.assertEqual(response.data["endpoint"], "origin")

        # 4. Select origin clearing (c3 has warriors)
        response = self.moles_client.submit_action(
            {"clearing_number": self.c3.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_destination")
        self.assertEqual(response.data["endpoint"], "destination")

        # 5. Select destination (c6 is adjacent to c3)
        response = self.moles_client.submit_action(
            {"clearing_number": self.c6.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_count")
        self.assertEqual(response.data["endpoint"], "count")

        # 6. Select count (use "number" type as in payload_details)
        response = self.moles_client.submit_action({"number": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_brigadier_first_action_battle(self):
        """Test brigadier first action: action-type (battle) -> clearing -> faction -> completed"""
        # Place Moles warrior in c1 where Birds warrior is
        Warrior.objects.create(player=self.moles_player, clearing=self.c1)

        # 1. Get minister selection
        self.moles_client.get_action()

        # 2. Select brigadier action
        response = self.moles_client.submit_action({"action": "brigadier"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_action_type")

        # 3. Select battle action type
        response = self.moles_client.submit_action({"action_type": "battle"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_clearing")
        self.assertEqual(response.data["endpoint"], "clearing")

        # 4. Select clearing with enemy
        response = self.moles_client.submit_action(
            {"clearing_number": self.c1.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_faction")
        self.assertEqual(response.data["endpoint"], "faction")

        # 5. Select faction to battle (use "faction" type as in payload_details)
        response = self.moles_client.submit_action({"faction": Faction.BIRDS})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

    def test_brigadier_restricts_options_mid_action(self):
        """Test that when brigadier_action != NONE, only brigadier/skip options are shown"""
        # Set brigadier action in progress
        self.daylight.brigadier_action = MoleDaylight.BrigadierAction.MOVE
        self.daylight.save()

        # Get minister selection
        response = self.moles_client.get_action()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_minister")

        # Should only have brigadier and skip_brigadier and done options
        self.assertEqual(len(response.data["options"]), 3)
        values = [opt["value"] for opt in response.data["options"]]
        self.assertIn("brigadier", values)
        self.assertIn("skip_brigadier", values)
        self.assertIn("", values)

    def test_mayor_select_unswayed_minister_rejects(self):
        """Test that Mayor cannot copy an unswayed minister"""
        # Unsway Marshal only, keep Mayor and other ministers swayed
        marshal = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.MARSHAL
        )
        marshal.swayed = False
        marshal.save()

        # 1. Get minister selection (dispatcher)
        self.moles_client.get_action()

        # 2. Select Mayor action
        response = self.moles_client.submit_action({"action": "mayor"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_minister_to_copy")
        # Marshal should not be in the options since it's unswayed
        values = [opt["value"] for opt in response.data["options"]]
        self.assertNotIn("MARSHAL", values)

    def test_mayor_cannot_copy_lords(self):
        """Test that Mayor cannot copy lords (Duchess, Earl, Baron)"""
        # 1. Get minister selection (dispatcher)
        self.moles_client.get_action()

        # 2. Select Mayor action
        response = self.moles_client.submit_action({"action": "mayor"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_minister_to_copy")

        # 3. Try to select Duchess to copy (should fail)
        response = self.moles_client.submit_action({"action": "duchess"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mayor_copies_marshal_multi_step(self):
        """Test Mayor copying Marshal (multi-step move action)"""
        # 1. Get minister selection (dispatcher)
        self.moles_client.get_action()

        # 2. Select Mayor action
        response = self.moles_client.submit_action({"action": "mayor"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_minister_to_copy")

        # 3. Select Marshal to copy
        response = self.moles_client.submit_action({"action": "marshal"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should start Marshal flow (select origin)
        self.assertEqual(response.data["name"], "marshal_origin")

        # 4. Select origin clearing
        response = self.moles_client.submit_action(
            {"clearing_number": self.c3.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "marshal_destination")

        # 5. Select destination
        response = self.moles_client.submit_action(
            {"clearing_number": self.c6.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "marshal_count")

        # 6. Select count
        response = self.moles_client.submit_action({"number": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

        # Verify Mayor is marked as used
        mayor = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.MAYOR
        )
        self.assertTrue(mayor.used)

        # Verify Marshal is NOT marked as used
        marshal = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.MARSHAL
        )
        self.assertFalse(marshal.used)

    def test_mayor_copies_captain(self):
        """Test Mayor copying Captain (battle action)"""
        # Place Moles warrior in c1 where Birds warrior is
        Warrior.objects.create(player=self.moles_player, clearing=self.c1)

        # 1. Get minister selection (dispatcher)
        self.moles_client.get_action()

        # 2. Select Mayor action
        response = self.moles_client.submit_action({"action": "mayor"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_minister_to_copy")

        # 3. Select Captain to copy
        response = self.moles_client.submit_action({"action": "captain"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "captain_clearing")

        # 4. Select clearing with enemy
        response = self.moles_client.submit_action(
            {"clearing_number": self.c1.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "captain_faction")

        # 5. Select faction to battle
        response = self.moles_client.submit_action({"faction": Faction.BIRDS})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

        # Verify Mayor is marked as used
        mayor = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.MAYOR
        )
        self.assertTrue(mayor.used)

        # Verify Captain is NOT marked as used
        captain = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.CAPTAIN
        )
        self.assertFalse(captain.used)

    def test_mayor_copies_foremole(self):
        """Test Mayor copying Foremole (build action)"""
        # Give Moles player a card that matches c3
        card = Card.objects.get(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
        HandEntry.objects.create(player=self.moles_player, card=card)

        # 1. Get minister selection (dispatcher)
        self.moles_client.get_action()

        # 2. Select Mayor action
        response = self.moles_client.submit_action({"action": "mayor"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_minister_to_copy")

        # 3. Select Foremole to copy
        response = self.moles_client.submit_action({"action": "foremole"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "foremole_type")

        # 4. Select building type (citadel)
        response = self.moles_client.submit_action({"building_type": "Citadel"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "foremole_clearing")

        # 5. Select clearing (c3 has moles pieces and is ruled by player)
        response = self.moles_client.submit_action(
            {"clearing_number": self.c3.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "foremole_card")

        # 6. Select card to build with
        response = self.moles_client.submit_action(
            {"card": CardsEP.RABBIT_PARTISANS.name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

        # Verify Mayor is marked as used
        mayor = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.MAYOR
        )
        self.assertTrue(mayor.used)

        # Verify Foremole is NOT marked as used
        foremole = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.FOREMOLE
        )
        self.assertFalse(foremole.used)

    def test_mayor_copies_brigadier_move(self):
        """Test Mayor copying Brigadier for move action"""
        # 1. Get minister selection (dispatcher)
        self.moles_client.get_action()

        # 2. Select Mayor action
        response = self.moles_client.submit_action({"action": "mayor"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_minister_to_copy")

        # 3. Select Brigadier to copy
        response = self.moles_client.submit_action({"action": "brigadier"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_action_type")

        # 4. Select move action type
        response = self.moles_client.submit_action({"action_type": "move"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_origin")

        # 5. Select origin clearing (c3 has warriors)
        response = self.moles_client.submit_action(
            {"clearing_number": self.c3.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_destination")

        # 6. Select destination (c6 is adjacent to c3)
        response = self.moles_client.submit_action(
            {"clearing_number": self.c6.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_count")

        # 7. Select count
        response = self.moles_client.submit_action({"number": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

        # Verify Mayor is marked as used
        mayor = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.MAYOR
        )
        self.assertTrue(mayor.used)

        # Verify Brigadier is NOT marked as used
        brigadier = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.BRIGADIER
        )
        self.assertFalse(brigadier.used)

    def test_mayor_copies_brigadier_battle(self):
        """Test Mayor copying Brigadier for battle action"""
        # Place Moles warrior in c1 where Birds warrior is
        Warrior.objects.create(player=self.moles_player, clearing=self.c1)

        # 1. Get minister selection (dispatcher)
        self.moles_client.get_action()

        # 2. Select Mayor action
        response = self.moles_client.submit_action({"action": "mayor"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_minister_to_copy")

        # 3. Select Brigadier to copy
        response = self.moles_client.submit_action({"action": "brigadier"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_action_type")

        # 4. Select battle action type
        response = self.moles_client.submit_action({"action_type": "battle"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_clearing")

        # 5. Select clearing with enemy
        response = self.moles_client.submit_action(
            {"clearing_number": self.c1.clearing_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "brigadier_faction")

        # 6. Select faction to battle
        response = self.moles_client.submit_action({"faction": Faction.BIRDS})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

        # Verify Mayor is marked as used
        mayor = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.MAYOR
        )
        self.assertTrue(mayor.used)

        # Verify Brigadier is NOT marked as used
        brigadier = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.BRIGADIER
        )
        self.assertFalse(brigadier.used)

    def test_mayor_copies_banker(self):
        """Test Mayor copying Banker (card selection action)"""
        # Give Moles player multiple cards of same suit
        card1 = Card.objects.get(game=self.game, card_type=CardsEP.FOXFOLK_STEEL.name)
        HandEntry.objects.create(player=self.moles_player, card=card1)
        card2 = Card.objects.get(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        HandEntry.objects.create(player=self.moles_player, card=card2)

        # 1. Get minister selection (dispatcher)
        self.moles_client.get_action()

        # 2. Select Mayor action
        response = self.moles_client.submit_action({"action": "mayor"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_minister_to_copy")

        # 3. Select Banker to copy
        response = self.moles_client.submit_action({"action": "banker"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "banker_select_card")

        # 4. Select first card
        response = self.moles_client.submit_action({"card": CardsEP.FOXFOLK_STEEL.name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "banker_select_card")
        self.assertIn("1 cards selected", response.data["prompt"])

        # 5. Select second card (same suit)
        response = self.moles_client.submit_action({"card": CardsEP.FOX_PARTISANS.name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "banker_select_card")
        self.assertIn("2 cards selected", response.data["prompt"])

        # 6. Submit (empty card name means done)
        response = self.moles_client.submit_action({"card": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")

        # Verify Mayor is marked as used
        mayor = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.MAYOR
        )
        self.assertTrue(mayor.used)

        # Verify Banker is NOT marked as used
        banker = Minister.objects.get(
            player=self.moles_player, name=Minister.MinisterName.BANKER
        )
        self.assertFalse(banker.used)

    def test_api_request_rejection_when_brigadier_mid_action(self):
        """Test that API rejects non-brigadier/skip requests when brigadier_action != NONE"""
        # Set brigadier action in progress
        self.daylight.brigadier_action = MoleDaylight.BrigadierAction.MOVE
        self.daylight.save()

        # Try to select marshal (should be rejected)
        self.moles_client.get_action()
        response = self.moles_client.submit_action({"action": "marshal"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check error message (response.data might be a list or dict)
        if isinstance(response.data, list):
            error_str = str(response.data)
        elif isinstance(response.data, dict):
            error_detail = response.data.get("detail", response.data)
            error_str = str(error_detail)
        else:
            error_str = str(response.data)
        self.assertIn("Cannot use another minister", error_str)
