"""Integration tests for Rats Daylight action views.

Tests cover:
  - RatsDaylightCraftView  (/api/rats/daylight/craft/)
  - RatsDaylightCommandView (/api/rats/daylight/command/)
  - RatsCommandMoveView    (/api/rats/daylight/command/move/)
  - RatsCommandBuildView   (/api/rats/daylight/command/build/)

Map reference (Autumn map, 1-indexed)
--------------------------------------
Fox (r):    1, 6, 8, 12
Rabbit (y): 3, 4, 5, 10
Mouse (o):  2, 7, 9, 11

Setup approach
--------------
1. GameSetupFactory(factions=[RATS, CATS])
2. Force game_setup.status = RATS_SETUP, pick corner 2 (mouse/orange), confirm.
3. Force game.current_turn to rats turn_order, status = SETUP_COMPLETED.
4. RatsTurn.create_turn(player), manually complete birdsong, set daylight step.

After pick_corner(player, c2):
  - Warlord placed at C2 (mouse)
  - 4 warriors at C2
  - 1 Stronghold placed in C2's building slot

C2 adjacencies: C5 (rabbit), C6 (fox), C10 (rabbit)
"""

from django.test import TestCase

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.enums import Faction
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import (
    Building,
    BuildingSlot,
    Card,
    Clearing,
    Game,
    HandEntry,
    Warrior,
)
from game.models.rats.buildings import Stronghold
from game.models.rats.player import CurrentMood
from game.models.rats.turn import RatsBirdsong, RatsDaylight, RatsTurn
from game.tests.client import RootGameClient
from game.tests.my_factories import GameSetupFactory
from game.transactions.rats_setup import (
    confirm_completed_setup as rats_confirm_setup,
    pick_corner as rats_pick_corner,
)


# ===========================================================================
# Shared base
# ===========================================================================


class RatsDaylightBaseTestCase(TestCase):
    """Creates a RATS + CATS game and completes setup so a RatsTurn can be created."""

    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.RATS, Faction.CATS])
        self.player = self.game.players.get(faction=Faction.RATS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)

        # Complete rats setup: force status, pick corner C2 (mouse/orange), confirm.
        game_setup = GameSimpleSetup.objects.get(game=self.game)
        game_setup.status = GameSimpleSetup.GameSetupStatus.RATS_SETUP
        game_setup.save()

        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        rats_pick_corner(self.player, self.c2)
        rats_confirm_setup(self.player)

        # Point game.current_turn at rats player and mark setup complete.
        self.game.refresh_from_db()
        self.game.current_turn = self.player.turn_order
        self.game.status = Game.GameStatus.SETUP_COMPLETED
        self.game.save()

        # Set up authenticated client for the rats player.
        self.player.user.set_password("password")
        self.player.user.save()
        self.rats_client = RootGameClient(
            self.player.user.username, "password", self.game.id
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_card_to_hand(self, card_enum: CardsEP) -> HandEntry:
        """Create a card of the given type and put it in the player's hand."""
        card = Card.objects.create(game=self.game, card_type=card_enum.name)
        return HandEntry.objects.create(player=self.player, card=card)

    def _deploy_stronghold(self, clearing: Clearing) -> Stronghold:
        """Move one supply Stronghold onto *clearing* into an available slot."""
        occupied_slot_ids = Building.objects.filter(
            building_slot__clearing=clearing
        ).values_list("building_slot_id", flat=True)
        slot = (
            BuildingSlot.objects.filter(clearing=clearing)
            .exclude(id__in=occupied_slot_ids)
            .first()
        )
        self.assertIsNotNone(
            slot,
            f"No available building slot in clearing {clearing.clearing_number}",
        )
        sh = Stronghold.objects.filter(
            player=self.player, building_slot__isnull=True
        ).first()
        self.assertIsNotNone(sh, "No Strongholds left in supply")
        sh.building_slot = slot
        sh.save()
        return sh

    def _place_warrior(self, clearing: Clearing, player=None) -> Warrior:
        """Move one supply warrior for *player* (default: self.player) into *clearing*."""
        if player is None:
            player = self.player
        w = Warrior.objects.filter(player=player, clearing__isnull=True).first()
        self.assertIsNotNone(w, "No warriors left in supply")
        w.clearing = clearing
        w.save()
        return w

    def _create_turn_at_craft(self):
        """Create a RatsTurn with birdsong COMPLETED and daylight at CRAFT."""
        self.rats_turn = RatsTurn.create_turn(self.player)
        birdsong = self.rats_turn.birdsong.first()
        birdsong.step = RatsBirdsong.Steps.COMPLETED
        birdsong.save()
        self.daylight = self.rats_turn.daylight.first()
        self.daylight.step = RatsDaylight.Steps.CRAFT
        self.daylight.save()

    def _create_turn_at_command(self):
        """Create a RatsTurn with birdsong COMPLETED and daylight at COMMAND."""
        self.rats_turn = RatsTurn.create_turn(self.player)
        birdsong = self.rats_turn.birdsong.first()
        birdsong.step = RatsBirdsong.Steps.COMPLETED
        birdsong.save()
        self.daylight = self.rats_turn.daylight.first()
        self.daylight.step = RatsDaylight.Steps.COMMAND
        self.daylight.save()


# ===========================================================================
# Craft view tests
# ===========================================================================


class RatsDaylightCraftRoutingTestCase(RatsDaylightBaseTestCase):
    """Tests for /api/rats/daylight/craft/ — routing and Done path."""

    def setUp(self):
        super().setUp()
        self._create_turn_at_craft()

    def test_craft_get_routes_to_craft(self):
        """get_action() should resolve to the craft route."""
        self.rats_client.get_action()
        self.assertEqual(
            self.rats_client.base_route,
            "/api/rats/daylight/craft/",
        )

    def test_craft_done_advances_step(self):
        """Posting card_to_craft='' (Done) should advance the daylight step past CRAFT."""
        self.rats_client.get_action()
        response = self.rats_client.submit_action({"card": ""})
        self.assertEqual(response.status_code, 200)

        self.daylight.refresh_from_db()
        self.assertNotEqual(
            self.daylight.step,
            RatsDaylight.Steps.CRAFT,
            "Daylight step should have advanced past CRAFT after Done Crafting",
        )

    def test_craft_get_returns_done_option(self):
        """GET response must include the 'Done Crafting' option (value='')."""
        response = self.rats_client.get_action()
        data = response.json()
        self.assertIn("options", data)
        option_values = [opt["value"] for opt in data["options"]]
        self.assertIn("", option_values, "Done Crafting option must appear in options")


# ===========================================================================
# Craft — single-stronghold card test
# ===========================================================================


class RatsDaylightCraftSingleCardTestCase(RatsDaylightBaseTestCase):
    """Tests that a single-orange-cost card can be crafted using the C2 Stronghold."""

    def setUp(self):
        super().setUp()
        self._create_turn_at_craft()
        # Give the player a Mouse-in-a-Sack (cost: 1 orange/mouse) — crafted using C2 stronghold.
        self._add_card_to_hand(CardsEP.MOUSE_IN_A_SACK)

    def test_craft_single_stronghold_card(self):
        """Crafting a 1-orange card using the C2 stronghold should succeed."""
        # Verify the C2 stronghold is placed and not yet used.
        stronghold = Stronghold.objects.filter(
            player=self.player,
            building_slot__clearing=self.c2,
            crafted_with=False,
        ).first()
        self.assertIsNotNone(stronghold, "C2 Stronghold should exist and be unused")

        self.rats_client.get_action()

        # Step 1: pick the card.
        response = self.rats_client.submit_action({"card": CardsEP.MOUSE_IN_A_SACK.name})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should now be at the clearing-selection step.
        self.assertIn("endpoint", data)
        self.assertEqual(data["endpoint"], "clearing")

        # Step 2: pick clearing 2 (the C2 orange stronghold).
        response = self.rats_client.submit_action({"clearing_number": 2})
        self.assertEqual(response.status_code, 200)

        # Card should be gone from hand.
        self.assertFalse(
            HandEntry.objects.filter(
                player=self.player, card__card_type=CardsEP.MOUSE_IN_A_SACK.name
            ).exists(),
            "Card should have been removed from hand after crafting",
        )

        # Stronghold should now be marked as crafted_with=True.
        stronghold.refresh_from_db()
        self.assertTrue(
            stronghold.crafted_with,
            "Stronghold should be marked crafted_with=True after use",
        )


# ===========================================================================
# Command view tests
# ===========================================================================


class RatsDaylightCommandRoutingTestCase(RatsDaylightBaseTestCase):
    """Tests for /api/rats/daylight/command/ — routing and Done path."""

    def setUp(self):
        super().setUp()
        self._create_turn_at_command()

    def test_command_get_routes_to_command(self):
        """get_action() should resolve to the command route."""
        self.rats_client.get_action()
        self.assertEqual(
            self.rats_client.base_route,
            "/api/rats/daylight/command/",
        )

    def test_command_done_advances_step(self):
        """Posting action='' (Done) should advance the daylight step past COMMAND."""
        self.rats_client.get_action()
        response = self.rats_client.submit_action({"action_type": ""})
        self.assertEqual(response.status_code, 200)

        self.daylight.refresh_from_db()
        self.assertNotEqual(
            self.daylight.step,
            RatsDaylight.Steps.COMMAND,
            "Daylight step should have advanced past COMMAND after Done",
        )

    def test_command_get_returns_expected_options(self):
        """GET response should include Move, Battle, Build, and Done options."""
        response = self.rats_client.get_action()
        data = response.json()
        self.assertIn("options", data)
        option_values = {opt["value"] for opt in data["options"]}
        self.assertIn("move", option_values)
        self.assertIn("battle", option_values)
        self.assertIn("build", option_values)
        self.assertIn("", option_values)  # Done


# ===========================================================================
# Command — Move redirect test
# ===========================================================================


class RatsDaylightCommandMoveTestCase(RatsDaylightBaseTestCase):
    """Tests for the Move sub-command path."""

    def setUp(self):
        super().setUp()
        self._create_turn_at_command()

    def test_command_move_redirect(self):
        """Posting action='move' should redirect to the move sub-view."""
        self.rats_client.get_action()
        # post_action sends the raw value without submit_action's payload mapping.
        self.rats_client.step = {
            "endpoint": "select",
            "payload_details": [{"type": "action_type", "name": "action"}],
        }
        response = self.rats_client.post_action({"action": "move"})
        # post_action follows the redirect automatically and returns the GET of the new view.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.rats_client.base_route,
            "/api/rats/daylight/command/move/",
        )

    def test_command_move_full_flow(self):
        """A full Move from C2 → C5 (adjacent) should move warriors and complete."""
        # C2 already has 4 warriors from setup. C5 is adjacent to C2.
        c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        warriors_in_c2_before = Warrior.objects.filter(
            player=self.player, clearing=self.c2
        ).count()
        self.assertGreater(warriors_in_c2_before, 0, "C2 should have Rats warriors")

        self.rats_client.get_action()

        # Select move action.
        self.rats_client.step = {
            "endpoint": "select",
            "payload_details": [{"type": "action_type", "name": "action"}],
        }
        response = self.rats_client.post_action({"action": "move"})
        self.assertEqual(response.status_code, 200)
        # Now at move sub-view — pick origin C2.
        response = self.rats_client.submit_action({"clearing_number": 2})
        self.assertEqual(response.status_code, 200)
        # Pick destination C5.
        response = self.rats_client.submit_action({"clearing_number": 5})
        self.assertEqual(response.status_code, 200)
        # Pick count = 1.
        response = self.rats_client.submit_action({"number": 1})
        self.assertEqual(response.status_code, 200)

        # Warrior count should have shifted.
        warriors_in_c2_after = Warrior.objects.filter(
            player=self.player, clearing=self.c2
        ).count()
        warriors_in_c5_after = Warrior.objects.filter(
            player=self.player, clearing=c5
        ).count()
        self.assertEqual(warriors_in_c2_after, warriors_in_c2_before - 1)
        self.assertEqual(warriors_in_c5_after, 1)

        # commands_used should have incremented.
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.commands_used, 1)


# ===========================================================================
# Command — Build redirect test
# ===========================================================================


class RatsDaylightCommandBuildTestCase(RatsDaylightBaseTestCase):
    """Tests for the Build sub-command path.

    Build requires:
      - A card in hand matching the suit of the target clearing.
      - Rats rule the clearing.
      - A free building slot in that clearing.
      - A Stronghold in supply.

    C2 (orange/mouse) already has a Stronghold from setup. We use a different
    clearing (C7, also orange/mouse) that the Rats may not rule yet. Instead, we
    deploy a warrior in C6 (fox) so Rats rule it (no other pieces), add a fox
    card to hand, and build there — C6 has free building slots and is adjacent
    to C2 for ruling purposes.

    Actually, simpler: after setup Rats rule C2. C2 already has one Stronghold
    which may consume the only building slot. Check if a free slot exists in C2;
    if not, use a clearing the Rats rule by placing a warrior (no other pieces).
    We'll use C5 (rabbit) — place a warrior there (Rats become ruler of C5 with
    no enemies), and spend a rabbit card to build.
    """

    def setUp(self):
        super().setUp()
        self._create_turn_at_command()

    def test_command_build_redirect(self):
        """Posting action='build' should redirect to the build sub-view."""
        self.rats_client.get_action()
        self.rats_client.step = {
            "endpoint": "select",
            "payload_details": [{"type": "action_type", "name": "action"}],
        }
        response = self.rats_client.post_action({"action": "build"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.rats_client.base_route,
            "/api/rats/daylight/command/build/",
        )

    def test_command_build_full_flow(self):
        """Full Build: place a Stronghold in C5 (rabbit) using a rabbit card.

        Setup: place a Rats warrior in C5 so Rats rule it.
        Hand: add a rabbit-suit card to hand.
        Execute: build → select card → select clearing C5.
        """
        c5 = Clearing.objects.get(game=self.game, clearing_number=5)

        # Place a Rats warrior in C5 so Rats rule it (no enemies, Rats have a piece).
        self._place_warrior(c5)

        # Add a rabbit (yellow) card to hand. RABBIT_PARTISANS is suit=YELLOW.
        # card_matches_clearing checks card.value.suit, not cost, so any yellow card works.
        self._add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        strongholds_in_supply_before = Stronghold.objects.filter(
            player=self.player, building_slot__isnull=True
        ).count()
        self.assertGreater(strongholds_in_supply_before, 0, "Need Strongholds in supply")

        self.rats_client.get_action()

        # Select build action.
        self.rats_client.step = {
            "endpoint": "select",
            "payload_details": [{"type": "action_type", "name": "action"}],
        }
        response = self.rats_client.post_action({"action": "build"})
        self.assertEqual(response.status_code, 200)

        # Now at build sub-view — pick card.
        response = self.rats_client.submit_action({"card": CardsEP.RABBIT_PARTISANS.name})
        self.assertEqual(response.status_code, 200)

        # Pick clearing C5.
        response = self.rats_client.submit_action({"clearing_number": 5})
        self.assertEqual(response.status_code, 200)

        # Stronghold should now be in C5.
        self.assertTrue(
            Stronghold.objects.filter(
                player=self.player, building_slot__clearing=c5
            ).exists(),
            "A Stronghold should have been placed in C5",
        )

        # Card should be gone from hand.
        self.assertFalse(
            HandEntry.objects.filter(
                player=self.player, card__card_type=CardsEP.RABBIT_PARTISANS.name
            ).exists(),
            "Card should have been discarded after building",
        )

        # commands_used should have incremented.
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.commands_used, 1)
