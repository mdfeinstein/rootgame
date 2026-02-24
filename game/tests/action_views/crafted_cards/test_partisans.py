from django.test import TestCase
from .client import RootGameClient
from game.models.game_models import Faction, Player, CraftedCardEntry, Clearing, Warrior, Card, HandEntry
from game.models.events.battle import Battle
from game.models.events.event import Event, EventType
from game.models.events.crafted_cards import PartisansEvent
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory, HandEntryFactory
from game.game_data.cards.exiles_and_partisans import CardsEP

class PartisansViewTestCase(TestCase):
    def setUp(self):
        # Create game with Cats and Birds
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Setup passwords for client login
        self.birds_player.user.set_password("password")
        self.birds_player.user.save()
        
        self.birds_client = RootGameClient(self.birds_player.user.username, "password", self.game.id)
        
        # Give Birds FOX_PARTISANS card
        self.card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        self.entry = CraftedCardEntryFactory(player=self.birds_player, card=self.card, used=CraftedCardEntry.UsedChoice.UNUSED)

        # Give Birds some cards (one fox, one mouse)
        self.fox_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name) # Fox
        self.mouse_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_ORANGE.name) # Mouse
        HandEntryFactory(player=self.birds_player, card=self.fox_card)
        HandEntryFactory(player=self.birds_player, card=self.mouse_card)

        # Setup battle in a Fox clearing (Clearing 2 in Autumn map is Fox? No, 1 is Fox. 2 is Mouse. 3 is Rabbit. 4 is Fox.)
        # Clearing 1 (Fox), Clearing 2 (Mouse), Clearing 3 (Rabbit), Clearing 4 (Fox)
        self.clearing = Clearing.objects.get(game=self.game, clearing_number=1)
        
        # Create Battle
        self.battle_event = Event.objects.create(game=self.game, type=EventType.BATTLE)
        self.battle = Battle.objects.create(
            event=self.battle_event,
            attacker=Faction.BIRDS,
            defender=Faction.CATS,
            clearing=self.clearing,
            step=Battle.BattleSteps.ROLL_DICE
        )
        
        # Create Partisans Event for Birds
        self.event_entry = PartisansEvent.create(self.battle, self.entry)

    def test_partisans_flow(self):
        """Test Partisans flow."""
        self.birds_client.base_route = "/api/action/card/partisans/"
        
        # 1. Initial GET -> use-or-skip
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.assertEqual(response.status_code, 200)
        self.birds_client.step = response.data
        self.assertEqual(response.data["name"], "use-or-skip")
        
        # 2. SUBMIT "use" -> completed
        response = self.birds_client.submit_action({"choice": "use"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify extra hit
        self.battle.refresh_from_db()
        self.assertEqual(self.battle.defender_hits_taken, 1)
        
        # Verify cards discarded (mouse card should be gone, fox card should remain)
        self.assertTrue(HandEntry.objects.filter(player=self.birds_player, card=self.fox_card).exists())
        self.assertFalse(HandEntry.objects.filter(player=self.birds_player, card=self.mouse_card).exists())

    def test_partisans_skip(self):
        """Test skipping Partisans."""
        self.birds_client.base_route = "/api/action/card/partisans/"
        
        response = self.birds_client.get(f"{self.birds_client.base_route}?game_id={self.game.id}")
        self.birds_client.step = response.data
        response = self.birds_client.submit_action({"choice": "skip"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "completed")
        
        # Verify no extra hit
        self.battle.refresh_from_db()
        self.assertEqual(self.battle.defender_hits_taken, 0)
        
        # Verify no cards discarded
        self.assertTrue(HandEntry.objects.filter(player=self.birds_player, card=self.fox_card).exists())
        self.assertTrue(HandEntry.objects.filter(player=self.birds_player, card=self.mouse_card).exists())
