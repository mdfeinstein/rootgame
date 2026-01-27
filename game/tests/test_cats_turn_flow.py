from game.transactions.cats import reset_cats_turn
from game.models import HandEntry
from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, Game, CraftedCardEntry
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory
from game.transactions.general import next_step
from game.models.cats.turn import CatTurn, CatBirdsong, CatDaylight, CatEvening
from game.game_data.cards.exiles_and_partisans import CardsEP

class CatTurnFlowTestCase(TestCase):
    def setUp(self):
        # Create a game with Cats, Birds, and WA
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE])
        
        # Identify players
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Set up client for Cats player
        self.cats_player.user.set_password("password")
        self.cats_player.user.save()
        self.cats_client = RootGameClient(self.cats_player.user.username, "password", self.game.id)
        
        # # Advance game to Cats' turn (turn 0)
        # self.game.current_turn = 0
        # self.game.save()
        
        # Initialize Cats' turn which should trigger Birdsong auto-placement
        # In actual game, this might have been called by next_players_turn from previous player
        # But for the test, we ensure it's in the starting state.
        # CatBirdsong default is NOT_STARTED. We need to move it to at least verify the auto-flow.
        # next_step(self.cats_player)
        cat_turn_count = CatTurn.objects.filter(player=self.cats_player).count()
        print(f"cat turn count: {cat_turn_count}")

    def test_cats_turn_flow(self):
        """
        Test moving through a Cats turn by ending all action steps.
        Wood should auto-place, move straight to Daylight.
        """
        cat_turn_count = CatTurn.objects.filter(player=self.cats_player).count()
        print(f"cat turn count: {cat_turn_count}")
        # 1. Birdsong check
        self.cats_client.get_action()
        # Since wood should auto-place, it should land on Daylight Crafting
        # (Birdsong NOT_STARTED -> PLACING_WOOD -> check_auto_place_wood -> next_step -> COMPLETED)
        # So current action should be 'cats-daylight-craft'
        self.assertEqual(self.cats_client.base_route, "/api/cats/daylight/craft/")
        
        # 2. Daylight - Crafting Step
        # End crafting step
        self.cats_client.submit_action({"card": ""})
        
        # 3. Daylight - Actions Step
        # It should move to 'cats-daylight-actions'
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.base_route, "/api/cats/daylight/actions/")
        # End action step
        self.cats_client.submit_action({"action_type": ""})
        
        # 4. Evening:
        # draw, discard, and end turn should happen automatically.
        # check for four cards in hand
        cards_in_hand = HandEntry.objects.filter(player=self.cats_player)
        self.assertEqual(cards_in_hand.count(), 4)
        # Verify turn advanced to Birds (turn order 1)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, 1)
        
        birds_player = self.game.players.get(turn_order=1)
        self.assertEqual(birds_player.faction, Faction.BIRDS)

    def test_cats_saboteurs_flow(self):
        """Test Saboteurs triggers at start of Birdsong (PLACING_WOOD step)"""
        saboteurs_card = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name, suit="w")
        CraftedCardEntryFactory(player=self.cats_player, card=saboteurs_card)
        
        # Reset turn
        CatTurn.objects.filter(player=self.cats_player).delete()
        CatTurn.create_turn(self.cats_player)
        
        #reset sawmills
        reset_cats_turn(self.cats_player)
        # next_step moves NOT_STARTED -> PLACING_WOOD -> triggers saboteurs_check
        next_step(self.cats_player)
        
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.base_route, "/api/action/card/saboteurs/")
        self.cats_client.submit_action({"faction": "skip"})
        
        # After skip, it should go back to PLACING_WOOD effects (auto place wood) and then to Daylight Crafting
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.base_route, "/api/cats/daylight/craft/")

    def test_cats_eyrie_emigre_flow(self):
        """Test Eyrie Emigre triggers when Birdsong completes"""
        emigre_card = CardFactory(game=self.game, card_type=CardsEP.EYRIE_EMIGRE.name, suit="w")
        CraftedCardEntryFactory(player=self.cats_player, card=emigre_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        turn = CatTurn.objects.filter(player=self.cats_player).order_by("-turn_number").first()
        birdsong = turn.birdsong
        birdsong.step = CatBirdsong.CatBirdsongSteps.COMPLETED
        birdsong.save()
        
        from game.transactions.cats import step_effect
        step_effect(self.cats_player, birdsong)
        
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.base_route, "/api/action/card/eyrie-emigre/")
        self.cats_client.submit_action({"choice": "skip"})
        
        # After skip, turn moves to Daylight CRAFTING
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.base_route, "/api/cats/daylight/craft/")

    def test_cats_charm_offensive_flow(self):
        """Test Charm Offensive triggers after Daylight ACTIONS completes"""
        charm_card = CardFactory(game=self.game, card_type=CardsEP.CHARM_OFFENSIVE.name, suit="y")
        CraftedCardEntryFactory(player=self.cats_player, card=charm_card)
        
        turn = CatTurn.objects.filter(player=self.cats_player).order_by("-turn_number").first()
        birdsong = turn.birdsong
        birdsong.step = CatBirdsong.CatBirdsongSteps.COMPLETED
        birdsong.save()
        
        daylight = turn.daylight
        daylight.step = CatDaylight.CatDaylightSteps.ACTIONS
        daylight.save()
        
        # End actions
        self.cats_client.get_action()
        self.cats_client.submit_action({"action_type": ""})
        
        # Should trigger charm offensive
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.base_route, "/api/action/card/charm-offensive/")
        self.cats_client.submit_action({"faction": "skip"})
        
        # After skip, turn should move through Evening drawing/discarding to next player
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, 1) # Birds turn


    def test_cats_informants_flow(self):
        """Test Informants triggers during Evening DRAWING step"""
        informants_card = CardFactory(game=self.game, card_type=CardsEP.INFORMANTS.name, suit="o")
        CraftedCardEntryFactory(player=self.cats_player, card=informants_card)
        
        turn = CatTurn.objects.filter(player=self.cats_player).order_by("-turn_number").first()
        birdsong = turn.birdsong
        birdsong.step = CatBirdsong.CatBirdsongSteps.COMPLETED
        birdsong.save()
        daylight = turn.daylight
        daylight.step = CatDaylight.CatDaylightSteps.COMPLETED
        daylight.save()
        
        from game.transactions.cats import step_effect
        # Moving to Evening phase (manually set steps to ensure we reach DRAWING)
        turn.evening.step = CatEvening.CatEveningSteps.DRAWING
        turn.evening.save()
        
        # Triggering evening drawing
        step_effect(self.cats_player, turn.evening)

        
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.base_route, "/api/action/card/informants/")
        self.cats_client.submit_action({"choice": "skip"})
        
        # Finishes turn (back to Birds)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, 1)
