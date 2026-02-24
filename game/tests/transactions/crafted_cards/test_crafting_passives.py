from django.test import TestCase
from game.models.game_models import Faction, Card, CraftedCardEntry, HandEntry, Item, CraftableItemEntry, DeckEntry
from game.tests.my_factories import GameSetupWithFactionsFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.general import craft_card
from game.game_data.general.game_enums import ItemTypes

class CraftingPassivesTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        
        # Ensure we have some cards in deck for Murine Brokers to draw
        DeckEntry.objects.filter(game=self.game).delete()
        cards = Card.objects.filter(game=self.game)
        for i, card in enumerate(cards[:10]):
            DeckEntry.objects.create(game=self.game, card=card, spot=i)

    def test_master_engravers_bonus(self):
        """Test +1 VP from Master Engravers when crafting an item."""
        # Give Cats Master Engravers
        card_me = Card.objects.filter(game=self.game, card_type=CardsEP.MASTER_ENGRAVERS.name).first()
        CraftedCardEntry.objects.create(player=self.cats_player, card=card_me)
        
        # Give Cats an item card (Foxfolk Steel, 2 VP)
        card_item = Card.objects.filter(game=self.game, card_type=CardsEP.FOXFOLK_STEEL.name).first()
        hand_item = HandEntry.objects.create(player=self.cats_player, card=card_item)
        
        # Ensure the item is in the craftable pool
        item_obj = Item.objects.create(game=self.game, item_type=ItemTypes.SWORD.value)
        CraftableItemEntry.objects.create(game=self.game, item=item_obj)
        
        # Craft it
        initial_score = self.cats_player.score
        craft_card(hand_item, []) 
        
        self.cats_player.refresh_from_db()
        # Foxfolk Steel is 2 VP + 1 from Master Engravers = 3
        self.assertEqual(self.cats_player.score, initial_score + 3)

    def test_murine_brokers_draw(self):
        """Test that Murine Brokers triggers a draw ONLY when another player crafts an ITEM."""
        # Give Birds Murine Brokers
        card_mb = Card.objects.filter(game=self.game, card_type=CardsEP.MURINE_BROKERS.name).first()
        CraftedCardEntry.objects.create(player=self.birds_player, card=card_mb)
        
        initial_birds_hand_size = HandEntry.objects.filter(player=self.birds_player).count()
        
        # 1. Cats craft a NON-ITEM card (e.g. Tunnels)
        card_tunnels = Card.objects.filter(game=self.game, card_type=CardsEP.TUNNELS.name).first()
        hand_tunnels = HandEntry.objects.create(player=self.cats_player, card=card_tunnels)
        
        craft_card(hand_tunnels, [])
        
        # Birds should NOT have drawn a card (not an item)
        self.assertEqual(HandEntry.objects.filter(player=self.birds_player).count(), initial_birds_hand_size)
        
        # 2. Cats craft an ITEM card (e.g. Foxfolk Steel)
        card_item1 = Card.objects.filter(game=self.game, card_type=CardsEP.FOXFOLK_STEEL.name).first()
        hand_item1 = HandEntry.objects.create(player=self.cats_player, card=card_item1)
        
        # Ensure item is in pool
        item_obj1 = Item.objects.create(game=self.game, item_type=ItemTypes.SWORD.value)
        CraftableItemEntry.objects.create(game=self.game, item=item_obj1)
        
        craft_card(hand_item1, [])
        
        # Birds should have drawn a card
        self.assertEqual(HandEntry.objects.filter(player=self.birds_player).count(), initial_birds_hand_size + 1)
        
        # 3. Cats craft ANOTHER ITEM card (e.g. Anvil) - should still trigger (no limit)
        card_item2 = Card.objects.filter(game=self.game, card_type=CardsEP.ANVIL.name).first()
        hand_item2 = HandEntry.objects.create(player=self.cats_player, card=card_item2)
        
        # Ensure item is in pool
        item_obj2 = Item.objects.create(game=self.game, item_type=ItemTypes.HAMMER.value)
        CraftableItemEntry.objects.create(game=self.game, item=item_obj2)
        
        craft_card(hand_item2, [])
        
        # Birds should have drawn ANOTHER card
        self.assertEqual(HandEntry.objects.filter(player=self.birds_player).count(), initial_birds_hand_size + 2)
