from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, Game, HandEntry, CraftedCardEntry

from game.tests.my_factories import (
    GameSetupWithFactionsFactory,
    CraftedCardEntryFactory,
    CardFactory,
)
from game.transactions.general import next_step
from game.models.wa.turn import WATurn, WABirdsong, WADaylight, WAEvening
from game.game_data.cards.exiles_and_partisans import CardsEP


class WATurnFlowTestCase(TestCase):
    def setUp(self):
        # Create a game with Cats, Birds, and WA
        self.game = GameSetupWithFactionsFactory(
            factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE]
        )

        # Identify players
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.wa_player = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)

        # Set up password first so login works
        self.wa_player.user.set_password("password")
        self.wa_player.user.save()

        # Set up client for WA player
        self.wa_client = RootGameClient(
            self.wa_player.user.username, "password", self.game.id
        )

        # Login again because the first one might have failed if password wasn't set
        self.wa_client.login()

        # Advance game to WA's turn
        self.game.current_turn = 2
        self.game.save()

        # Initialize WA's turn
        next_step(self.wa_player)

    def test_wa_turn_flow(self):
        """
        Test moving through a WA turn by ending all action steps.
        """
        # 1. Birdsong - Revolt Step
        self.wa_client.get_action()
        # Initial action should be WA_REVOLT
        self.assertEqual(self.wa_client.base_route, "/api/wa/birdsong/revolt/")
        # End revolt step. Depending on supporters, it might be 'clearing_number' or 'confirm'
        if "clearing_number" in [
            d["type"] for d in self.wa_client.step["payload_details"]
        ]:
            self.wa_client.submit_action({"clearing_number": ""})
        else:
            self.wa_client.submit_action({"confirm": True})

        # 2. Birdsong - Spread Sympathy Step
        # After completing revolt, it should move to WA_SPREAD_SYMPATHY
        self.assertEqual(self.wa_client.base_route, "/api/wa/birdsong/spread-sympathy/")
        # End spread sympathy step
        if "clearing_number" in [
            d["type"] for d in self.wa_client.step["payload_details"]
        ]:
            self.wa_client.submit_action({"clearing_number": ""})
        else:
            self.wa_client.submit_action({"confirm": True})

        # 3. Daylight - Actions Step
        # After completing spread sympathy, it should move to WA_DAYLIGHT_ACTIONS
        self.assertEqual(self.wa_client.base_route, "/api/wa/daylight/actions/")
        # End daylight actions
        self.wa_client.submit_action({"action_type": ""})

        # 4. Evening - Military Operations Step
        # After completing daylight actions, it should move to WA_EVENING (Military Operations)
        self.assertEqual(self.wa_client.base_route, "/api/wa/evening/operations/")
        # End operations
        if "action_type" in [d["type"] for d in self.wa_client.step["payload_details"]]:
            self.wa_client.submit_action({"action_type": ""})
        else:
            self.wa_client.submit_action({"confirm": True})

        # 5. Evening - Drawing and Discarding
        # end_evening_operations calls next_step which moves to DRAWING.
        # step_effect for DRAWING calls draw_cards and then next_step (if no informants).
        # draw_cards calls next_step.
        # So it might skip DISCARDING if hand size <= 5.

        # Verify that turn has advanced back to the first player (Cats, turn order 0)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, 0)

    def test_wa_saboteurs_flow(self):
        """
        Test that Saboteurs triggers at start of WA Birdsong and can be skipped.
        """
        # Give WA the Saboteurs card
        saboteurs_card = CardFactory(
            game=self.game, card_type=CardsEP.SABOTEURS.name, suit="w"
        )
        CraftedCardEntryFactory(player=self.wa_player, card=saboteurs_card)

        # Reset turn to test from start
        WATurn.objects.filter(player=self.wa_player).delete()
        WATurn.create_turn(self.wa_player)

        # Initial step NOT_STARTED -> next_step moves to REVOLT
        # step_effect for REVOLT calls saboteurs_check
        next_step(self.wa_player)

        # Now get_action should return saboteurs
        self.wa_client.get_action()
        self.assertEqual(self.wa_client.base_route, "/api/action/card/saboteurs/")

        # Skip saboteurs
        self.wa_client.submit_action({"faction": "skip"})

        # After skip, it should move to REVOLT
        self.wa_client.get_action()
        self.assertEqual(self.wa_client.base_route, "/api/wa/birdsong/revolt/")

    def test_wa_charm_offensive_flow(self):
        """
        Test that Charm Offensive triggers after WA Daylight and can be skipped.
        """
        # Give WA the Charm Offensive card
        charm_card = CardFactory(
            game=self.game, card_type=CardsEP.CHARM_OFFENSIVE.name, suit="y"
        )
        CraftedCardEntryFactory(player=self.wa_player, card=charm_card)

        # Move to Daylight Actions step
        from game.queries.wa.turn import get_phase

        turn = WATurn.objects.get(player=self.wa_player)
        birdsong = WABirdsong.objects.get(turn=turn)
        birdsong.step = WABirdsong.WABirdsongSteps.COMPLETED
        birdsong.save()

        daylight = WADaylight.objects.get(turn=turn)
        daylight.step = WADaylight.WADaylightSteps.ACTIONS
        daylight.save()

        # End daylight actions
        self.wa_client.get_action()
        self.assertEqual(self.wa_client.base_route, "/api/wa/daylight/actions/")
        self.wa_client.submit_action({"action_type": ""})

        # After daylight actions, it moves to Daylight COMPLETED, which triggers check_charm_offensive
        self.wa_client.get_action()
        self.assertEqual(self.wa_client.base_route, "/api/action/card/charm-offensive/")

        # Skip charm offensive
        self.wa_client.submit_action({"select": "skip"})

        # After skip, turn should move to Evening military operations
        self.wa_client.get_action()
        self.assertEqual(self.wa_client.base_route, "/api/wa/evening/operations/")

    def test_wa_informants_flow(self):
        """
        Test that Informants triggers during WA Drawing step and can be skipped.
        """
        # Give WA the Informants card
        informants_card = CardFactory(
            game=self.game, card_type=CardsEP.INFORMANTS.name, suit="o"
        )
        CraftedCardEntryFactory(player=self.wa_player, card=informants_card)

        # Move to Evening Military Operations step
        turn = WATurn.objects.get(player=self.wa_player)
        WABirdsong.objects.filter(turn=turn).update(
            step=WABirdsong.WABirdsongSteps.COMPLETED
        )
        WADaylight.objects.filter(turn=turn).update(
            step=WADaylight.WADaylightSteps.COMPLETED
        )
        evening = WAEvening.objects.get(turn=turn)
        evening.step = WAEvening.WAEveningSteps.MILITARY_OPERATIONS
        evening.save()

        # End military operations
        self.wa_client.get_action()
        self.assertEqual(self.wa_client.base_route, "/api/wa/evening/operations/")
        if "action_type" in [d["type"] for d in self.wa_client.step["payload_details"]]:
            self.wa_client.submit_action({"action_type": ""})
        else:
            self.wa_client.submit_action({"confirm": True})

        # Now get_action should return informants if we are in DRAWING step

        # end_evening_operations calls next_step which moves to DRAWING, triggering informants
        self.wa_client.get_action()
        self.assertEqual(self.wa_client.base_route, "/api/action/card/informants/")

        # Skip informants
        self.wa_client.submit_action({"choice": "skip"})

        # After skip, it should draw and end turn (if hand size <= 5)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, 0)  # Back to Cats

    def test_wa_eyrie_emigre_flow(self):
        """
        Test that Eyrie Emigre triggers after WA Birdsong and can be skipped.
        """
        # Give WA the Eyrie Emigre card
        emigre_card = CardFactory(
            game=self.game, card_type=CardsEP.EYRIE_EMIGRE.name, suit="w"
        )
        CraftedCardEntryFactory(
            player=self.wa_player,
            card=emigre_card,
            used=CraftedCardEntry.UsedChoice.UNUSED,
        )

        # Move to Birdsong COMPLETED step
        turn = WATurn.objects.get(player=self.wa_player)
        birdsong = WABirdsong.objects.get(turn=turn)
        birdsong.step = WABirdsong.WABirdsongSteps.COMPLETED
        birdsong.save()

        from game.transactions.wa import step_effect

        step_effect(self.wa_player, birdsong)

        # Now get_action should return eyrie-emigre
        self.wa_client.get_action()
        self.assertEqual(self.wa_client.base_route, "/api/action/card/eyrie-emigre/")

        # Skip eyrie-emigre
        self.wa_client.submit_action({"choice": "skip"})

        # After skip, it should move to Daylight ACTIONS
        self.wa_client.get_action()
        self.assertEqual(self.wa_client.base_route, "/api/wa/daylight/actions/")
