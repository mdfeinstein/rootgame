from django.test import TestCase
from game.models.game_models import Faction, Card, CraftedCardEntry, HandEntry, Clearing, Suit
from game.models.events.battle import Battle
from game.models.events.event import Event, EventType
from game.models.events.crafted_cards import PartisansEvent
from game.tests.my_factories import GameSetupWithFactionsFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.battle import roll_dice, use_partisans, skip_partisans

class PartisansTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        
        # Setup clearings
        self.fox_clearing = Clearing.objects.filter(game=self.game, suit=Suit.RED).first()
        self.rabbit_clearing = Clearing.objects.filter(game=self.game, suit=Suit.YELLOW).first()
        
        # Ensure pieces are in clearing for the battle
        from game.models import Warrior
        Warrior.objects.create(player=self.cats_player, clearing=self.fox_clearing)
        Warrior.objects.create(player=self.birds_player, clearing=self.fox_clearing)
        
        # Setup hands - Clear existing first
        HandEntry.objects.filter(player=self.cats_player).delete()
        HandEntry.objects.filter(player=self.birds_player).delete()

    def test_partisans_extra_hit_and_discard(self):
        """Test that Partisans gives extra hit and discards non-matching cards."""
        # Give Cats Fox Partisans
        card_fp = Card.objects.filter(game=self.game, card_type=CardsEP.FOX_PARTISANS.name).first()
        CraftedCardEntry.objects.create(player=self.cats_player, card=card_fp)
        
        # Setup Cats hand
        fox_card = Card.objects.filter(game=self.game, suit=Suit.RED).exclude(card_type=CardsEP.FOX_PARTISANS.name).first()
        rabbit_card = Card.objects.filter(game=self.game, suit=Suit.YELLOW).first()
        bird_card = Card.objects.filter(game=self.game, suit=Suit.WILD).first()
        
        HandEntry.objects.create(player=self.cats_player, card=fox_card)
        HandEntry.objects.create(player=self.cats_player, card=rabbit_card)
        HandEntry.objects.create(player=self.cats_player, card=bird_card)
        
        # Start a battle
        event = Event.objects.create(game=self.game, type=EventType.BATTLE)
        battle = Battle.objects.create(
            event=event,
            attacker=Faction.CATS,
            defender=Faction.BIRDS,
            clearing=self.fox_clearing,
            step=Battle.BattleSteps.ROLL_DICE
        )
        
        # Roll dice - should launch PartisansEvent for Cats (attacker) 
        # because Birds (defender) don't have partisans.
        roll_dice(self.game, battle)
        
        partisan_event = PartisansEvent.objects.get(battle=battle, event__is_resolved=False)
        self.assertEqual(partisan_event.crafted_card_entry.player, self.cats_player)
        
        # Use Partisans
        initial_defender_hits = battle.defender_hits_taken
        use_partisans(self.game, battle, partisan_event)
        
        # Verify discard: Fox card should stay, Rabbit and Bird should be gone
        hand = HandEntry.objects.filter(player=self.cats_player)
        self.assertEqual(hand.count(), 1)
        self.assertEqual(hand.first().card.suit, Suit.RED)
        
        battle.refresh_from_db()
        # Defender hits should have increased by 1
        self.assertEqual(battle.defender_hits_taken, initial_defender_hits + 1)

    def test_partisans_order_defender_then_attacker(self):
        """Test that defender gets prompted for Partisans before attacker."""
        # Both have Fox Partisans
        card_fp_cats = Card.objects.filter(game=self.game, card_type=CardsEP.FOX_PARTISANS.name).first()
        CraftedCardEntry.objects.create(player=self.cats_player, card=card_fp_cats)
        
        card_fp_birds = Card.objects.create(
            game=self.game, 
            card_type=CardsEP.FOX_PARTISANS.name, 
            suit=Suit.RED
        )
        CraftedCardEntry.objects.create(player=self.birds_player, card=card_fp_birds)
        
        # Start a battle
        event = Event.objects.create(game=self.game, type=EventType.BATTLE)
        battle = Battle.objects.create(
            event=event,
            attacker=Faction.CATS,
            defender=Faction.BIRDS,
            clearing=self.fox_clearing,
            step=Battle.BattleSteps.ROLL_DICE
        )
        
        # Roll dice - should launch PartisansEvent for Birds (defender) first
        roll_dice(self.game, battle)
        
        partisan_event_defender = PartisansEvent.objects.get(battle=battle, event__is_resolved=False)
        self.assertEqual(partisan_event_defender.crafted_card_entry.player, self.birds_player)
        
        # Defender skips
        skip_partisans(self.game, battle, partisan_event_defender)
        
        # Now should launch PartisansEvent for Cats (attacker)
        partisan_event_attacker = PartisansEvent.objects.get(battle=battle, event__is_resolved=False)
        self.assertEqual(partisan_event_attacker.crafted_card_entry.player, self.cats_player)
