from game.models.game_models import Warrior
from game.models.birds.turn import BirdBirdsong
from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, Game, HandEntry, Clearing
from game.tests.my_factories import GameSetupWithFactionsFactory
from game.transactions.general import next_step
from game.models.birds.player import BirdLeader, DecreeEntry, Vizier
from game.game_data.cards.exiles_and_partisans import CardsEP

class BirdTurnFlowTestCase(TestCase):
    def setUp(self):
        # Create a game with Cats, Birds, and WA
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE])
        
        # Identify players
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        
        # Set up client for Birds player
        # We need to make sure the user is set up with a password
        self.birds_player.user.set_password("password")
        self.birds_player.user.save()
        self.birds_client = RootGameClient(self.birds_player.user.username, "password", self.game.id)
        
        # Advance game to Birds' turn
        self.game.current_turn = 1
        self.game.save()
        
        # Initial setup for Birds: 1 roost in clearing 3. Despot leader.
        # Despot Viziers: Move, Build.
        # Birdsong: Hand size 3.
        
        # Create turn if not exists
        from game.models.birds.turn import BirdTurn
        if not BirdTurn.objects.filter(player=self.birds_player).exists():
            BirdTurn.create_turn(self.birds_player)
            
        # Initial state should be Birdsong NOT_STARTED.
        # Calling next_step will trigger auto-flow through EMERGENCY_DRAWING to ADD_TO_DECREE.
        next_step(self.birds_player)

    def test_birds_turn_flow(self):
        """
        Test moving through a Birds turn.
        Add card to Recruit, skip craft, recruit, move, build, and verify evening.
        """
        # 1. Birdsong: Add to decree (Recruit)
        from game.queries.general import get_current_player
        from game.queries.birds.turn import get_phase
        cp = get_current_player(self.game)
        phase = get_phase(self.birds_player)
        print(f"DEBUG: current_turn={self.game.current_turn}, current_player={cp.faction}, phase={type(phase).__name__}, step={phase.step}")
        
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/birds/birdsong/add-to-decree/")
        
        # Pick a card from hand to add to Recruit
        hand_card = HandEntry.objects.filter(player=self.birds_player).first()
        self.birds_client.submit_action({"card": hand_card.card.card_type})
        
        # Select column Recruit
        self.birds_client.submit_action({"decree_column": "RECRUIT"})
        
        # Done adding to decree
        self.birds_client.submit_action({"card": ""})
        
        # 2. Daylight: Crafting
        # Auto-skips through EMERGENCY_ROOSTING (has roost) and lands on CRAFTING
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/birds/daylight/craft/")
        # Skip craft
        self.birds_client.submit_action({"card": ""})
        
        # 3. Daylight: Recruiting
        # Lands on RECRUITING because we added a card to Recruit column.
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/birds/daylight/recruit/")
        # Recruit in clearing 3 (where the roost is).
        self.birds_client.submit_action({"clearing_number": 3})
        
        # 4. Daylight: Moving
        # Moves to MOVING because Recruit card fulfilled.
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/birds/daylight/move/")
        # Move from 3 to 7 (connected in Autumn).
        # Submit origin
        self.birds_client.submit_action({"clearing_number": 3})
        # Submit destination
        self.birds_client.submit_action({"clearing_number": 7})
        # Submit count
        self.birds_client.submit_action({"number": 1})
        
        # 5. Daylight: Building
        # BATTLING skipped (no cards/viziers), moves to BUILDING.
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/birds/daylight/building/")
        # Build in 7.
        self.birds_client.submit_action({"clearing_number": 7})
        
        # 6. Evening:
        # BUILDING fulfilled, auto-moves through Evening.
        self.game.refresh_from_db()
        # Next turn order is 2 (WA)
        self.assertEqual(self.game.current_turn, 2)
        
        # Check hand size
        # Hand was 3. -1 for decree. Hand = 2.
        # Roosts: started with 1, built 1 = 2.
        # draw cards: drawing_per_roost_on_board[2] = 1.
        # Total = 3.
        hand_size = HandEntry.objects.filter(player=self.birds_player).count()
        self.assertEqual(hand_size, 3)

    def test_birds_saboteurs_flow(self):
        """
        Test that Saboteurs triggers at start of Birdsong and can be skipped to move to Add to Decree.
        """
        from game.tests.my_factories import CraftedCardEntryFactory, CardFactory
        # Give Birds the Saboteurs card
        saboteurs_card = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name, suit="w")
        CraftedCardEntryFactory(player=self.birds_player, card=saboteurs_card)
        
        # Reset turn to test from start
        from game.models.birds.turn import BirdTurn
        BirdTurn.objects.filter(player=self.birds_player).delete()
        BirdTurn.create_turn(self.birds_player)
        
        # Initial step NOT_STARTED -> next_step moves to EMERGENCY_DRAWING
        # step_effect for EMERGENCY_DRAWING calls saboteurs_check, which creates the event.
        next_step(self.birds_player)
        
        # Now get_action should return saboteurs
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/action/card/saboteurs/")
        
        # Skip saboteurs
        # Based on my change to SaboteursView, it expects "faction": "skip" in "pick-faction" route
        self.birds_client.submit_action({"faction": "skip"})
        
        # After skip, it should move to Add to Decree (since Emergency Drawing is automated)
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/birds/birdsong/add-to-decree/")

    def test_birds_charm_offensive_flow(self):
        """
        Test that Charm Offensive triggers after Building and can be skipped to end turn.
        """
        from game.queries.birds.turn import get_phase
        from game.tests.my_factories import CraftedCardEntryFactory, CardFactory
        # Give Birds the Charm Offensive card
        charm_card = CardFactory(game=self.game, card_type=CardsEP.CHARM_OFFENSIVE.name, suit="y")
        CraftedCardEntryFactory(player=self.birds_player, card=charm_card)
        
        # skip to building step by completing birdsong and setting daylight 
        birdsong = get_phase(self.birds_player)
        assert type(birdsong) == BirdBirdsong, "Not birdsong phase in the test!"
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()

        daylight = get_phase(self.birds_player)
        from game.models.birds.turn import BirdDaylight
        assert type(daylight) == BirdDaylight, "Not daylight phase in the test!"
        daylight.step = BirdDaylight.BirdDaylightSteps.BUILDING
        daylight.save()
        # Build in clearing where they don't have a roost and no one else is(clearing 4)
        # need to add a warrior in clearing 4
        clearing4 = Clearing.objects.get(game=self.game, clearing_number=4)
        warrior = Warrior.objects.filter(player=self.birds_player, clearing__isnull=True).first() 
        warrior.clearing = clearing4
        warrior.save()
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/birds/daylight/building/")
        self.birds_client.submit_action({"clearing_number": 4})
        print(self.birds_client.last_post_response.json())
        # After building, it moves to Daylight COMPLETED, which triggers check_charm_offensive.
        # check_charm_offensive launches the event.

        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/action/card/charm-offensive/")
        
        # Skip charm offensive
        self.birds_client.submit_action({"faction": "skip"})
        
        # After skip, turn should move through Evening scoring/drawing/discarding to next player
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, 2) # WA turn

    def test_birds_informants_flow(self):
        """
        Test that Informants triggers during Drawing step and can be skipped.
        """
        from game.tests.my_factories import CraftedCardEntryFactory, CardFactory
        # Give Birds the Informants card
        informants_card = CardFactory(game=self.game, card_type=CardsEP.INFORMANTS.name, suit="o")
        CraftedCardEntryFactory(player=self.birds_player, card=informants_card)
        
        # Move to Evening phase, NOT_STARTED step
        from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening
        from game.queries.birds.turn import validate_turn
        turn = validate_turn(self.birds_player)
        birdsong = BirdBirdsong.objects.get(turn=turn)
        daylight = BirdDaylight.objects.get(turn=turn)
        evening = BirdEvening.objects.get(turn=turn)
        
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()
        daylight.step = BirdDaylight.BirdDaylightSteps.COMPLETED
        daylight.save()
        evening.step = BirdEvening.BirdEveningSteps.SCORING
        evening.save()
        # Call next_step to move to DRAWING, which should trigger informants
        next_step(self.birds_player)
        # Now get_action should return informants
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/action/card/informants/")
        
        # Skip informants
        self.birds_client.submit_action({"choice": "skip"})
        
        # After skip, it should draw and end turn
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_turn, 2) # WA turn
        
        # Check that card was drawn
        # started with 3. -0 for decree in this case. 1 drawn during evening. Total 4.
        hand_size = HandEntry.objects.filter(player=self.birds_player).count()
        self.assertEqual(hand_size, 4)
