from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, Warrior, Building, Clearing, Token, HandEntry, Card, Suit
from game.models.cats.buildings import Sawmill, Workshop, Recruiter
from game.models.cats.tokens import CatWood
from game.models.checkpoint_models import Checkpoint, Action
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, HandEntryFactory
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
        
        self.cats_client = RootGameClient(self.cats_player.user.username, "password", self.game.id)
        self.birds_client = RootGameClient(self.birds_player.user.username, "password", self.game.id)

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
        
        sawmill_count_before = Sawmill.objects.filter(player=self.cats_player, building_slot__isnull=False).count()
        
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
        new_count = Sawmill.objects.filter(player=self.cats_player, building_slot__isnull=False).count()
        self.assertEqual(new_count, sawmill_count_before + 1)
        
        # 4. Undo
        self.cats_client.post(f"/api/game/undo/{self.game.id}/")
        
        # 5. Verify state restored
        self.assertEqual(Sawmill.objects.filter(player=self.cats_player, building_slot__isnull=False).count(), sawmill_count_before)

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
        DecreeEntry.objects.create(player=self.birds_player, column=DecreeEntry.Column.BATTLE, card=CardFactory(game=self.game, card_type="AMBUSH_WILD"))
        
        # Set Birds to Battling step
        daylight = turn.daylight.first()
        daylight.step = daylight.BirdDaylightSteps.BATTLING
        daylight.save()
        
        # Start Battle
        self.birds_client.get_action()
        self.birds_client.submit_action({"clearing_number": clearing.clearing_number})
        self.birds_client.submit_action({"faction": Faction.CATS.name})
        
        # Defender (Cats) skips ambush.
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.step["name"], "ambush-check-defender")
        self.cats_client.submit_action({"card": ""})
        
        # Capture battle results
        from game.models.events.battle import Battle
        battle = Battle.objects.order_by("-id").first()
        hits_attacker = battle.attacker_hits_taken
        hits_defender = battle.defender_hits_taken
        
        # 2. Undo
        self.birds_client.post(f"/api/game/undo/{self.game.id}/")
        
        # 3. Repeat
        self.cats_client.get_action()
        self.cats_client.submit_action({"card": ""})
        
        # 4. Compare
        battle_replayed = Battle.objects.order_by("-id").first()
        self.assertEqual(hits_attacker, battle_replayed.attacker_hits_taken, "Attacker hits changed upon replay!")
        self.assertEqual(hits_defender, battle_replayed.defender_hits_taken, "Defender hits changed upon replay!")

    def test_undo_across_turn_boundary(self):
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

        for _ in range(5-cards_in_hand):
            HandEntryFactory(player=self.cats_player)
            
        self.cats_client.get_action()
        if self.cats_client.step["name"] == "draw_cards":
            self.cats_client.submit_action({"confirm": True})
        
        # 2. Discard card -> Finishes turn
        self.assertEqual(self.cats_client.step["name"], "discard_card")
        card_to_discard = HandEntry.objects.filter(player=self.cats_player).first().card.enum.name
        print(f"card to discard: {card_to_discard}")
        print(f"cards in hand: {cards_in_hand}")
        self.cats_client.submit_action({"card": card_to_discard})
        self.cats_client.get_action()
        print(self.cats_client.step)
        # Now it should be Birds turn
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, self.birds_player.turn_order)
        
        # 3. Birds undo
        # Birds client need to get action first to be in a valid view state? 
        # Actually undo is a global endpoint.
        self.birds_client.post(f"/api/game/undo/{self.game.id}/")
        
        # 4. Verify back in Cats turn (Discarding step)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, self.cats_player.turn_order)
        self.cats_client.get_action()
        self.assertEqual(self.cats_client.step["name"], "discard_card")
