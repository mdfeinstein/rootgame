from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, Game, HandEntry, Clearing, Warrior
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening, BirdTurn
from game.transactions.general import next_step
from game.models.events.crafted_cards import EyrieEmigreEvent

class EyrieEmigreTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE])
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        self.birds_player.user.set_password("password")
        self.birds_player.user.save()
        self.birds_client = RootGameClient(self.birds_player.user.username, "password", self.game.id)
        
        # Give Birds Eyrie Emigre
        emigre_card = CardFactory(game=self.game, card_type=CardsEP.EYRIE_EMIGRE.name, suit="w")
        from game.models.game_models import CraftedCardEntry
        self.emigre_entry = CraftedCardEntryFactory(player=self.birds_player, card=emigre_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Advance to Birds turn
        self.game.current_turn = 1
        self.game.save()
        
        if not BirdTurn.objects.filter(player=self.birds_player).exists():
            BirdTurn.create_turn(self.birds_player)

    def test_eyrie_emigre_flow(self):
        """Test full Eyrie Emigre flow: trigger at Birdsong end -> move -> battle -> card used."""
        turn = BirdTurn.objects.filter(player=self.birds_player).order_by("-turn_number").first()
        birdsong = BirdBirdsong.objects.get(turn=turn)
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()
        
        from game.transactions.birds import step_effect
        # Must pass birdsong phase explicitly to trigger the COMPLETED case
        step_effect(self.birds_player, birdsong)
        
        # Should now have an Eyrie Emigre event
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/action/card/eyrie-emigre/")
        
        # Step 1: Use
        self.birds_client.submit_action({"choice": "use"})
        
        # Step 2: Origin (Clearing 3 has a roost/warriors)
        self.birds_client.submit_action({"clearing_number": 3})
        
        # Step 3: Destination (Clearing 7 is connected)
        self.birds_client.submit_action({"clearing_number": 7})
        
        # Step 4: Count
        # Add a warrior to 3 just in case
        Warrior.objects.create(player=self.birds_player, clearing=Clearing.objects.get(game=self.game, clearing_number=3))
        # Add an enemy to 7 to avoid auto-failure
        Warrior.objects.create(player=self.cats_player, clearing=Clearing.objects.get(game=self.game, clearing_number=7))
        
        self.birds_client.submit_action({"number": 1})
        
        # Step 5: Battle Choice
        self.birds_client.get_action()
        self.assertEqual(self.birds_client.base_route, "/api/action/card/eyrie-emigre/")
        self.assertEqual(self.birds_client.step["name"], "battle-choice")
        
        self.birds_client.submit_action({"choice": "battle"})
        
        # Step 6: Select Faction
        self.birds_client.submit_action({"faction": "CATS"})
        
        # Should be completed and move back to Daylight CRAFTING
        self.game.refresh_from_db()
        from game.queries.birds.turn import get_phase
        phase = get_phase(self.birds_player)
        self.assertEqual(type(phase), BirdDaylight)
        self.assertEqual(phase.step, BirdDaylight.BirdDaylightSteps.CRAFTING)
        
        # Card should be used
        self.emigre_entry.refresh_from_db()
        self.assertEqual(self.emigre_entry.used, self.emigre_entry.UsedChoice.USED)

    def test_eyrie_emigre_skip(self):
        """Test skipping Eyrie Emigre."""
        turn = BirdTurn.objects.filter(player=self.birds_player).order_by("-turn_number").first()
        birdsong = BirdBirdsong.objects.get(turn=turn)
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()
        
        from game.transactions.birds import step_effect
        step_effect(self.birds_player, birdsong)
        
        self.birds_client.get_action()
        self.birds_client.submit_action({"choice": "skip"})
        
        # Event should be resolved and turn should proceed to Daylight CRAFTING
        self.game.refresh_from_db()
        from game.queries.birds.turn import get_phase
        phase = get_phase(self.birds_player)
        self.assertEqual(type(phase), BirdDaylight)
        self.assertEqual(phase.step, BirdDaylight.BirdDaylightSteps.CRAFTING)
        
        # Card should be marked as used
        self.emigre_entry.refresh_from_db()
        self.assertEqual(self.emigre_entry.used, self.emigre_entry.UsedChoice.USED)
