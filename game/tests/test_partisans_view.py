from django.test import TestCase
from django.urls import reverse
from game.models.game_models import Faction, Card, CraftedCardEntry, Clearing, Suit
from game.models.events.battle import Battle
from game.models.events.event import Event, EventType
from game.models.events.crafted_cards import PartisansEvent
from game.tests.my_factories import GameSetupWithFactionsFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.current_action.events import get_current_event_action
from game.tests.client import RootGameClient
from django.utils import timezone
from datetime import timedelta

class PartisansViewRoutingTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        # Set password for RootGameClient to work
        self.cats_player.user.set_password("password")
        self.cats_player.user.save()
        
        # Setup clearings
        self.fox_clearing = Clearing.objects.filter(game=self.game, suit=Suit.RED).first()
        
        # Setup Partisans
        card_fp = Card.objects.filter(game=self.game, card_type=CardsEP.FOX_PARTISANS.name).first()
        self.crafted_entry = CraftedCardEntry.objects.create(player=self.cats_player, card=card_fp)
        
        # Start a battle - backdate it so it's not the "current" event if partisans is launched
        self.event = Event.objects.create(game=self.game, type=EventType.BATTLE)
        Event.objects.filter(id=self.event.id).update(created_at=timezone.now() - timedelta(minutes=1))
        self.event.refresh_from_db()

        self.battle = Battle.objects.create(
            event=self.event,
            attacker=Faction.CATS,
            defender=Faction.BIRDS,
            clearing=self.fox_clearing,
            step=Battle.BattleSteps.ROLL_DICE
        )

    def test_partisans_event_routing(self):
        """Test that get_current_event_action returns the Partisans URL when an event is active."""
        # Create a Partisans event
        partisan_event = PartisansEvent.create(self.battle, self.crafted_entry)
        
        print(f"Total events: {Event.objects.filter(game=self.game).count()}")
        for e in Event.objects.filter(game=self.game).order_by("-created_at"):
            print(f"Event ID: {e.id}, Type: {e.type}, Created: {e.created_at}")
            
        # Check routing
        action_url = get_current_event_action(self.game)
        self.assertEqual(action_url, reverse("partisans"))
        
    def test_partisans_view_get(self):
        """Test the PartisansView GET request returns the correct prompt and options."""
        partisans_event = PartisansEvent.create(self.battle, self.crafted_entry)
        
        client = RootGameClient(user=self.cats_player.user.username, password="password", game_id=self.game.id)
        response = client.get(reverse("partisans"), {"game_id": self.game.id})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["name"], "use-or-skip")
        self.assertIn(" Fox cards", data["prompt"])
        self.assertEqual(len(data["options"]), 2)
        self.assertEqual(data["accumulated_payload"]["event_entry_id"], partisans_event.id)

    def test_partisans_view_post_use(self):
        """Test that posting 'use' to PartisansView triggers use_partisans."""
        partisans_event = PartisansEvent.create(self.battle, self.crafted_entry)
        
        client = RootGameClient(user=self.cats_player.user.username, password="password", game_id=self.game.id)
        
        client.get_action() 
        
        response = client.submit_action({"choice": "use"})
        self.assertEqual(response.status_code, 200)
        
        # Verify event resolved
        partisans_event.refresh_from_db()
        self.assertTrue(partisans_event.event.is_resolved)
        
        # Verify battle updated (extra hit)
        self.battle.refresh_from_db()
        self.assertEqual(self.battle.defender_hits_taken, 1)

        #verify that all events are resolved (partisans event resolves, battle continues until resolution in this case)
        self.assertEqual(Event.objects.filter(game=self.game, is_resolved=True).count(), Event.objects.filter(game=self.game).count())

    def test_partisans_view_post_skip(self):
        """Test that posting 'skip' to PartisansView triggers skip_partisans."""
        partisans_event = PartisansEvent.create(self.battle, self.crafted_entry)
        
        client = RootGameClient(user=self.cats_player.user.username, password="password", game_id=self.game.id)
        
        client.get_action() 
        
        response = client.submit_action({"choice": "skip"})
        self.assertEqual(response.status_code, 200)
        
        # Verify event resolved
        partisans_event.refresh_from_db()
        self.assertTrue(partisans_event.event.is_resolved)
        
        # Verify battle NOT updated
        self.battle.refresh_from_db()
        self.assertEqual(self.battle.defender_hits_taken, 0)
        
        #verify that all events are resolved 
        self.assertEqual(Event.objects.filter(game=self.game, is_resolved=True).count(), Event.objects.filter(game=self.game).count())
