from game.queries.birds.turn import get_phase
from game.models import EventType
from game.models.events import Event
from game.models.events import Battle
from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import (
    Faction,
    Player,
    Warrior,
    Building,
    Clearing,
    Token,
    HandEntry,
    Card,
    Suit,
)
from game.models.cats.buildings import Sawmill, Workshop, Recruiter
from game.models.cats.tokens import CatWood
from game.models.checkpoint_models import Checkpoint, Action
from game.tests.my_factories import (
    GameSetupWithFactionsFactory,
    CardFactory,
    HandEntryFactory,
)
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.player import DecreeEntry, BirdLeader, Vizier
from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening
import random


class UndoMechanicsTestCase(TestCase):
    def setUp(self):
        # Create game with Cats and Birds
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)

        # Setup passwords for client login
        self.cats_player.user.set_password("password")
        self.cats_player.user.save()
        self.birds_player.user.set_password("password")
        self.birds_player.user.save()

        self.cats_client = RootGameClient(
            self.cats_player.user.username, "password", self.game.id
        )
        self.birds_client = RootGameClient(
            self.birds_player.user.username, "password", self.game.id
        )

    def test_basic_undo(self):
        """Test simple undo of a single action."""
        self.game.current_turn = self.cats_player.turn_order
        self.game.save()

        from game.models.cats.turn import CatTurn

        turn = CatTurn.create_turn(self.cats_player)
        turn.birdsong.step = turn.birdsong.CatBirdsongSteps.COMPLETED
        turn.birdsong.save()
        turn.daylight.step = turn.daylight.CatDaylightSteps.ACTIONS
        turn.daylight.save()

        self.cats_client.get_action()
        self.assertEqual(self.cats_client.step["name"], "select_action")

        clearing = Clearing.objects.get(game=self.game, clearing_number=5)
        # Ensure Cats rule clearing 5 for building
        Warrior.objects.create(player=self.cats_player, clearing=clearing)

        # Place Exactly 1 wood token in clearing 1
        CatWood.objects.filter(player=self.cats_player).delete()
        CatWood.objects.create(player=self.cats_player, clearing=clearing)

        sawmill_count_before = Sawmill.objects.filter(
            player=self.cats_player, building_slot__isnull=False
        ).count()

        # 1. Start build
        self.cats_client.submit_action({"action_type": "build"})
        # 2. Pick building
        self.cats_client.submit_action({"building_type": "sawmill"})
        # 3. Pick clearing
        response = self.cats_client.submit_action({"clearing_number": 5})

        # If it asks for wood selection, handle it
        if self.cats_client.step["name"] == "select_build_wood":
            self.cats_client.submit_action({"clearing_number": 5})

        # Verify state changed (we check building count)
        new_count = Sawmill.objects.filter(
            player=self.cats_player, building_slot__isnull=False
        ).count()
        self.assertEqual(new_count, sawmill_count_before + 1)

        # 4. Undo
        self.cats_client.post(f"/api/game/undo/{self.game.id}/")

        # 5. Verify state restored
        self.assertEqual(
            Sawmill.objects.filter(
                player=self.cats_player, building_slot__isnull=False
            ).count(),
            sawmill_count_before,
        )

    def test_undo_across_phase_boundary(self):
        """Test undoing an action that transitions the phase."""
        from game.models.cats.turn import CatTurn

        turn = CatTurn.create_turn(self.cats_player)
        turn.birdsong.step = turn.birdsong.CatBirdsongSteps.COMPLETED
        turn.birdsong.save()
        turn.daylight.step = turn.daylight.CatDaylightSteps.ACTIONS
        turn.daylight.save()

        self.game.current_turn = self.cats_player.turn_order
        self.game.save()

        # Give Cats 6 cards so they don't auto-skip Discarding
        for _ in range(6):
            HandEntryFactory(player=self.cats_player)

        self.cats_client.get_action()
        # Finish daylight actions -> SHOULD transition to Evening
        self.cats_client.submit_action({"action_type": ""})

        # Verify now in Evening
        self.cats_client.get_action()
        self.assertIn("evening", self.cats_client.base_route)

        # If at draw_cards, submit it to get to discard_card
        print(self.cats_client.step)
        if self.cats_client.step["name"] == "draw_cards":
            self.cats_client.submit_action({"confirm": True})

        self.assertEqual(self.cats_client.step["name"], "discard_card")

        # Undo
        self.cats_client.post(f"/api/game/undo/{self.game.id}/")

        # Verify back in Daylight
        self.cats_client.get_action()
        self.assertIn("daylight", self.cats_client.base_route)
        self.assertEqual(self.cats_client.step["name"], "select_action")

    def test_battle_replay_determinism(self):
        """Test if battle rolls are deterministic upon undo/replay."""
        # 1. Setup Battle
        clearing = Clearing.objects.get(game=self.game, clearing_number=1)
        Warrior.objects.create(player=self.cats_player, clearing=clearing)
        Warrior.objects.create(player=self.birds_player, clearing=clearing)

        # Advance to Birds turn, Daylight
        from game.models.birds.turn import BirdTurn

        self.game.current_turn = self.birds_player.turn_order
        self.game.save()
        turn = BirdTurn.create_turn(self.birds_player)
        birdsong = turn.birdsong.first()
        birdsong.step = birdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()

        # Clear Viziers
        Vizier.objects.filter(player=self.birds_player).delete()

        # Setup Birds decree for battle - Use AMBUSH_WILD
        DecreeEntry.objects.create(
            player=self.birds_player,
            column=DecreeEntry.Column.BATTLE,
            card=CardFactory(game=self.game, card_type="AMBUSH_WILD"),
        )

        # Set Birds to Battling step
        daylight = turn.daylight.first()
        daylight.step = daylight.BirdDaylightSteps.BATTLING
        daylight.save()

        # Start Battle
        self.birds_client.get_action()
        self.birds_client.submit_action({"clearing_number": clearing.clearing_number})
        self.birds_client.submit_action({"faction": Faction.CATS.name})

        # Defender (Cats) skips ambush. This triggers roll_dice and creates a checkpoint AFTER.
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.step["name"], "ambush-check-defender")
        self.cats_client.submit_action({"card": ""})

        # Capture battle results
        from game.models.events.battle import Battle

        battle = Battle.objects.order_by("-id").first()
        hits_attacker = battle.attacker_hits_taken
        hits_defender = battle.defender_hits_taken

        # 2. Perform another action (Birds finishing daylight/evening)
        self.birds_client.get_action()

        # If still in daylight battle, we might need to skip the rest of the column
        if self.birds_client.step["name"] == "battling":
            # Use key 'clearing' because that's the type in payload_details
            self.birds_client.submit_action({"clearing": ""})

        checkpoints = Checkpoint.objects.filter(game=self.game).order_by("id")
        print(f"DEBUG: Checkpoints count: {checkpoints.count()}")
        for cp in checkpoints:
            actions = Action.objects.filter(checkpoint=cp).order_by("action_number")
            print(
                f"  CP {cp.id}: actions {[a.transaction_name.split('.')[-1] for a in actions]}"
            )

        # 3. Undo the LAST action (which was the skip battle action)
        print(f"DEBUG: Undoing last action...")
        self.birds_client.post(f"/api/game/undo/{self.game.id}/")

        # 4. Verify battle results still same
        battle_replayed = Battle.objects.get(pk=battle.pk)
        print(
            f"DEBUG: Battle results BEFORE: Attacker Hits={hits_attacker}, Defender Hits={hits_defender}"
        )
        print(
            f"DEBUG: Battle results AFTER UNDO: Attacker Hits={battle_replayed.attacker_hits_taken}, Defender Hits={battle_replayed.defender_hits_taken}"
        )
        self.assertEqual(
            hits_attacker,
            battle_replayed.attacker_hits_taken,
            "Attacker hits changed upon undo of subsequent action!",
        )
        self.assertEqual(
            hits_defender,
            battle_replayed.defender_hits_taken,
            "Defender hits changed upon undo of subsequent action!",
        )

    def test_undo_across_turn_boundary_fails(self):
        """Test undoing from start of Birds turn back to end of Cats turn."""
        from game.models.cats.turn import CatTurn

        turn = CatTurn.create_turn(self.cats_player)
        turn.birdsong.step = turn.birdsong.CatBirdsongSteps.COMPLETED
        turn.birdsong.save()
        turn.daylight.step = turn.daylight.CatDaylightSteps.COMPLETED
        turn.daylight.save()

        self.game.current_turn = self.cats_player.turn_order
        self.game.save()

        # Give Cats 5 cards (they already have 3 probably)
        cards_in_hand = HandEntry.objects.filter(player=self.cats_player).count()

        for _ in range(5 - cards_in_hand):
            HandEntryFactory(player=self.cats_player)
        # Give birds a saboteurs
        card = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name)
        HandEntryFactory(player=self.birds_player, card=card)
        # final steps of cat turn...
        self.cats_client.get_action()
        if self.cats_client.step["name"] == "draw_cards":
            self.cats_client.submit_action({"confirm": True})

        # 2. Discard card -> Finishes turn
        self.assertEqual(self.cats_client.step["name"], "discard_card")
        card_to_discard = (
            HandEntry.objects.filter(player=self.cats_player).first().card.enum.name
        )
        print(f"card to discard: {card_to_discard}")
        print(f"cards in hand: {cards_in_hand}")
        self.cats_client.submit_action({"card": card_to_discard})
        self.cats_client.get_action()
        print(self.cats_client.step)
        # Now it should be Birds turn
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, self.birds_player.turn_order)

        # 3. Birds do something (add sabo to decree) then undo
        sabos_in_hand = HandEntry.objects.filter(
            player=self.birds_player, card__card_type=CardsEP.SABOTEURS.name
        ).count()
        birdsong = get_phase(self.birds_player)
        self.assertEqual(birdsong.step, BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE)
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.step["name"], "add_to_decree")
        # pick sabo to go to recruit
        self.birds_client.submit_action({"card": "SABOTEURS"})
        self.assertEqual(self.birds_client.step["name"], "select_decree_column")
        self.birds_client.submit_action({"decree_column": "RECRUIT"})
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.step["name"], "add_to_decree")
        # check that hand card has been spent
        self.assertEqual(
            HandEntry.objects.filter(player=self.birds_player, card=card).count(),
            sabos_in_hand - 1,
        )
        self.birds_client.post(f"/api/game/undo/{self.game.id}/")
        # assert we have undone by checking if sabo is back in hand
        self.assertEqual(
            HandEntry.objects.filter(player=self.birds_player, card=card).count(),
            sabos_in_hand,
        )

        # 4. Then birds undo again, but nothign changes because we are at the turn boundary
        self.birds_client.post(f"/api/game/undo/{self.game.id}/")
        birdsong = get_phase(self.birds_player)
        self.assertEqual(birdsong.step, BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE)
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.step["name"], "add_to_decree")

    def test_battle_undo_preserves_deterministic_choice(self):
        """Test that undoing an action after a non-undoable action doesn't re-execute the non-undoable one."""
        # 1. Setup Battle
        clearing = Clearing.objects.get(game=self.game, clearing_number=1)
        Warrior.objects.create(player=self.cats_player, clearing=clearing)
        Warrior.objects.create(player=self.birds_player, clearing=clearing)

        # Give Cats a fox ambush card (clearing 1 is fox)
        from game.models.game_models import Card, HandEntry

        cats_ambush = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntryFactory(player=self.cats_player, card=cats_ambush)

        from game.models.birds.turn import BirdTurn

        self.game.current_turn = self.birds_player.turn_order
        self.game.save()
        turn = BirdTurn.create_turn(self.birds_player)
        turn.birdsong.all().update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)

        Vizier.objects.filter(player=self.birds_player).delete()
        DecreeEntry.objects.create(
            player=self.birds_player,
            column=DecreeEntry.Column.BATTLE,
            card=CardFactory(game=self.game, card_type="AMBUSH_WILD"),
        )

        daylight = turn.daylight.first()
        daylight.step = daylight.BirdDaylightSteps.BATTLING
        daylight.save()

        # Start Battle
        self.birds_client.get_action()
        self.birds_client.submit_action({"clearing_number": clearing.clearing_number})
        self.birds_client.submit_action({"faction": Faction.CATS.name})

        # Checkpoint state: [Bird Battle Action].
        # Defender (Cats) chooses ambush. This IS undoable=False.
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.step["name"], "ambush-check-defender")

        checkpoints_before = Checkpoint.objects.filter(game=self.game).count()

        # This execution will create a NEW checkpoint AFTER it completes because undoable=False
        # Use key "card" as expected by RootGameClient (it maps it to ambush_card)
        self.cats_client.submit_action({"card": CardsEP.AMBUSH_RED.name})

        checkpoints_after = Checkpoint.objects.filter(game=self.game).count()
        self.assertGreaterEqual(
            checkpoints_after,
            checkpoints_before + 1,
            "A new checkpoint should have been created after non-undoable action",
        )

        # Now Birds (Attacker) chooses ambush.
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.step["name"], "ambush-cancel-check-attacker")

        last_checkpoint = Checkpoint.objects.order_by("id").last()
        actions_in_new_checkpoint = Action.objects.filter(
            checkpoint=last_checkpoint
        ).count()

        # This one is also undoable=False, so it will create another checkpoint
        self.birds_client.submit_action({"card": ""})

        self.assertGreaterEqual(
            Checkpoint.objects.filter(game=self.game).count(), checkpoints_after + 1
        )

        # Now we are at Battle results or further.
        # Let's undo. It shouldn't do anything
        self.birds_client.post(f"/api/game/undo/{self.game.id}/")

        # Verify battle is over by checking that there is no unresolved battle
        battle_event = Event.objects.filter(
            game=self.game, is_resolved=False, type=EventType.BATTLE
        ).first()
        if battle_event:
            battle = Battle.objects.get(event=battle_event)
            step = Battle.BattleSteps(battle.step)
            self.assertFalse(
                step == Battle.BattleSteps.ATTACKER_AMBUSH_CANCEL_CHECK,
                f"After undo, Battle was found, and reverted to step: {step.name}",
            )
