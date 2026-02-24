from django.test import TestCase
from game.models.game_models import Faction, Game, HandEntry, Card, Suit, Player
from game.models.dominance import DominanceSupplyEntry, ActiveDominanceEntry
from game.transactions.dominance import swap_dominance, activate_dominance
from game.transactions.general import discard_card_from_hand, raise_score
from game.tests.my_factories import (
    GameSetupWithFactionsFactory,
    CardFactory,
    HandEntryFactory,
)
from game.tests.client import RootGameClient
from rest_framework.exceptions import ValidationError


from game.game_data.cards.exiles_and_partisans import CardsEP


class DominanceTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)

        self.cats_player.user.set_password("password")
        self.cats_player.user.save()
        self.client = RootGameClient(
            self.cats_player.user.username, "password", self.game.id
        )
        self.client.login()

    def test_discard_to_supply(self):
        # Create a dominance card in hand
        dom_card = CardFactory(
            game=self.game, card_type=CardsEP.DOMINANCE_RED.name, suit=Suit.RED
        )
        hand_entry = HandEntryFactory(player=self.cats_player, card=dom_card)

        # Discard it
        discard_card_from_hand(self.cats_player, hand_entry)

        # Check it is NOT in discard pile
        self.assertFalse(self.game.discardpileentry_set.filter(card=dom_card).exists())

        # Check it IS in dominance supply
        self.assertTrue(
            DominanceSupplyEntry.objects.filter(game=self.game, card=dom_card).exists()
        )

    def test_swap_dominance_transaction(self):
        # Setup: Dominance card in supply, matching suit card in hand
        dom_card = CardFactory(
            game=self.game, card_type=CardsEP.DOMINANCE_RED.name, suit=Suit.RED
        )
        DominanceSupplyEntry.objects.create(game=self.game, card=dom_card)

        match_card = CardFactory(game=self.game, suit=Suit.RED)
        hand_entry = HandEntryFactory(player=self.cats_player, card=match_card)

        # Execute swap
        swap_dominance(
            self.cats_player,
            hand_entry,
            DominanceSupplyEntry.objects.get(game=self.game, card=dom_card),
        )

        # Verify:
        # 1. Player has dominance card in hand
        self.assertTrue(
            HandEntry.objects.filter(player=self.cats_player, card=dom_card).exists()
        )
        # 2. Matching card is in discard (Wait, swap logic says matching card goes to ? supply? No, rules say "discard the card you swap for")
        # Let's check the rules/implementation. Usually you discard the card you pay with?
        # Actually in Root, you "spend" a card of matching suit. Spent usually means discard.
        # But wait, does the spent card go to the supply? No, standard discard.
        # The DOMINANCE card comes FROM the supply.
        # Let's check if the spent card is in discard pile.
        self.assertTrue(self.game.discardpileentry_set.filter(card=match_card).exists())
        # 3. Dominance card removed from supply
        self.assertFalse(
            DominanceSupplyEntry.objects.filter(game=self.game, card=dom_card).exists()
        )

    def test_swap_dominance_bird_card(self):
        # Setup: Dominance card in supply, Bird card in hand
        dom_card = CardFactory(
            game=self.game, card_type=CardsEP.DOMINANCE_RED.name, suit=Suit.RED
        )
        DominanceSupplyEntry.objects.create(game=self.game, card=dom_card)

        bird_card = CardFactory(game=self.game, suit=Suit.WILD)
        hand_entry = HandEntryFactory(player=self.cats_player, card=bird_card)

        # Execute swap
        swap_dominance(
            self.cats_player,
            hand_entry,
            DominanceSupplyEntry.objects.get(game=self.game, card=dom_card),
        )

        self.assertTrue(
            HandEntry.objects.filter(player=self.cats_player, card=dom_card).exists()
        )

    def test_activate_dominance_transaction(self):
        # Setup: Dominance card in hand, Score >= 10
        dom_card = CardFactory(
            game=self.game, card_type=CardsEP.DOMINANCE_RED.name, suit=Suit.RED
        )
        HandEntryFactory(player=self.cats_player, card=dom_card)

        self.cats_player.score = 10
        self.cats_player.save()

        # View passed 'card_in_hand_id'. Transaction signature: (player, card_in_hand_id/card_id?)
        # Let's verify signature in a moment. Assuming it takes HandEntry ID based on view.
        # Wait, I need the HandEntry ID.
        hand_entry = HandEntry.objects.get(player=self.cats_player, card=dom_card)
        activate_dominance(self.cats_player, hand_entry)

        # Verify:
        # 1. ActiveDominanceEntry created
        self.assertTrue(
            ActiveDominanceEntry.objects.filter(
                player=self.cats_player, card=dom_card
            ).exists()
        )
        # 2. Card removed from hand
        self.assertFalse(
            HandEntry.objects.filter(player=self.cats_player, card=dom_card).exists()
        )
        # 3. Card NOT in discard
        self.assertFalse(self.game.discardpileentry_set.filter(card=dom_card).exists())

    def test_activate_dominance_low_score_fail(self):
        dom_card = CardFactory(
            game=self.game, card_type=CardsEP.DOMINANCE_RED.name, suit=Suit.RED
        )
        hand_entry = HandEntryFactory(player=self.cats_player, card=dom_card)

        self.cats_player.score = 9
        self.cats_player.save()

        with self.assertRaises(ValueError):
            activate_dominance(self.cats_player, hand_entry)

    def test_scoring_lock(self):
        # Activate dominance
        dom_card = CardFactory(
            game=self.game, card_type=CardsEP.DOMINANCE_RED.name, suit=Suit.RED
        )
        ActiveDominanceEntry.objects.create(player=self.cats_player, card=dom_card)

        initial_score = self.cats_player.score

        # Try to raise score
        raise_score(self.cats_player, 5)

        self.cats_player.refresh_from_db()
        self.assertEqual(self.cats_player.score, initial_score)

    def test_swap_dominance_view(self):
        # Setup
        dom_card_enum = CardsEP.DOMINANCE_RED
        dom_card = CardFactory(game=self.game, card_type=dom_card_enum.name, suit="r")
        DominanceSupplyEntry.objects.create(game=self.game, card=dom_card)

        match_card_enum = CardsEP.FOX_PARTISANS
        match_card = CardFactory(
            game=self.game, card_type=match_card_enum.name, suit="r"
        )
        hand_entry = HandEntryFactory(player=self.cats_player, card=match_card)

        # 1. GET - check options
        response = self.client.get(
            "/api/action/dominance/swap/", {"game_id": self.game.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "select_dominance")
        self.assertEqual(len(response.data["options"]), 1)
        self.assertEqual(response.data["options"][0]["value"], dom_card_enum.name)

        # 2. POST select_dominance
        response = self.client.post(
            f"/api/action/dominance/swap/{self.game.id}/select_dominance/",
            {"dominance_card_name": dom_card_enum.name},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "swap")
        # Check matching options
        self.assertTrue(
            any(
                opt["value"] == match_card_enum.name for opt in response.data["options"]
            )
        )

        # 3. POST swap
        response = self.client.post(
            f"/api/action/dominance/swap/{self.game.id}/swap/",
            {
                "dominance_card_name": dom_card_enum.name,
                "card_to_discard_name": match_card_enum.name,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")

        # Verify state
        self.assertTrue(
            HandEntry.objects.filter(player=self.cats_player, card=dom_card).exists()
        )
