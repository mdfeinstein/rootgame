from django.test import TestCase
from django.contrib.auth.models import User
from game.models.game_models import Game, Player, Clearing, Faction, Suit, BuildingSlot
from game.models.birds.buildings import BirdRoost
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.birds.crafting import validate_crafting_pieces_satisfy_requirements
from game.models.game_models import (
    Card,
    HandEntry,
    CraftedCardEntry,
    Item,
    CraftableItemEntry,
    CraftedItemEntry,
)
from game.transactions.general import craft_card


class CraftingLogicTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")
        self.game = Game.objects.create(owner=self.user)
        self.player = Player.objects.create(
            game=self.game, faction=Faction.BIRDS, user=self.user
        )
        self.fox_clearing = Clearing.objects.create(
            game=self.game, suit=Suit.RED, clearing_number=1
        )  # RED=FOX
        self.mouse_clearing = Clearing.objects.create(
            game=self.game, suit=Suit.ORANGE, clearing_number=2
        )  # ORANGE=MOUSE
        self.rabbit_clearing = Clearing.objects.create(
            game=self.game, suit=Suit.YELLOW, clearing_number=3
        )  # YELLOW=RABBIT

    def create_roost(self, clearing):
        slot = BuildingSlot.objects.create(clearing=clearing, building_slot_number=1)
        return BirdRoost.objects.create(player=self.player, building_slot=slot)

    def test_soup_kitchens_out_of_order(self):
        # Card: SOUP_KITCHENS. Cost: [RED, YELLOW, ORANGE]
        # Pieces: [ORANGE, YELLOW, RED]
        # If order enforced by bug, this will fail.

        roost_orange = self.create_roost(self.mouse_clearing)
        roost_yellow = self.create_roost(self.rabbit_clearing)
        roost_red = self.create_roost(self.fox_clearing)

        card = CardsEP.SOUP_KITCHENS
        roosts = [roost_orange, roost_yellow, roost_red]

        validate_crafting_pieces_satisfy_requirements(self.player, card, roosts)

    def test_propaganda_bureau_all_wild(self):
        # Card: PROPAGANDA_BUREAU. Cost: [WILD, WILD, WILD]
        # Pieces: [RED, ORANGE, YELLOW]
        roost_red = self.create_roost(self.fox_clearing)
        roost_orange = self.create_roost(self.mouse_clearing)
        roost_yellow = self.create_roost(self.rabbit_clearing)

        card = CardsEP.PROPAGANDA_BUREAU
        roosts = [roost_red, roost_orange, roost_yellow]

        validate_crafting_pieces_satisfy_requirements(self.player, card, roosts)

    def test_duplicate_piece_usage(self):
        # Card: EYRIE_EMIGRE. Cost: [RED, RED]
        # Piece: [Roost(RED), Roost(RED)] (Same object)
        roost_red = self.create_roost(self.fox_clearing)
        card = CardsEP.EYRIE_EMIGRE
        roosts = [roost_red, roost_red]  # Duplicate!

        with self.assertRaises(ValueError):
            validate_crafting_pieces_satisfy_requirements(self.player, card, roosts)

    def test_cannot_craft_duplicate_card(self):
        # Player cannot craft a card (like Saboteurs) if they already have it.
        card_type = CardsEP.SABOTEURS
        card = Card.objects.create(game=self.game, card_type=card_type.name)
        CraftedCardEntry.objects.create(player=self.player, card=card)

        # Another instance of the same card in hand
        card_in_hand = Card.objects.create(game=self.game, card_type=card_type.name)
        hand_entry = HandEntry.objects.create(player=self.player, card=card_in_hand)

        with self.assertRaises(ValueError) as cm:
            craft_card(hand_entry, [])
        self.assertEqual(str(cm.exception), "player already has this card type crafted")

    def test_can_craft_duplicate_item_if_in_pool(self):
        # Player can craft an item if they already have that same item, provided it is in the pool.
        card_type = CardsEP.TRAVEL_GEAR_RED  # One of the boot cards
        item_type = Item.ItemTypes.BOOTS

        # Player already has a boot
        boot_item1 = Item.objects.create(game=self.game, item_type=item_type)
        CraftedItemEntry.objects.create(player=self.player, item=boot_item1)

        # Another boot is available in the pool
        boot_item2 = Item.objects.create(game=self.game, item_type=item_type)
        CraftableItemEntry.objects.create(game=self.game, item=boot_item2)

        card_in_hand = Card.objects.create(game=self.game, card_type=card_type.name)
        hand_entry = HandEntry.objects.create(player=self.player, card=card_in_hand)

        # Should NOT raise ValueError
        craft_card(hand_entry, [])
        self.assertTrue(
            CraftedItemEntry.objects.filter(
                player=self.player, item=boot_item2
            ).exists()
        )

    def test_cannot_craft_item_if_not_in_pool(self):
        # A player cannot craft an item that is no longer in the pool.
        card_type = CardsEP.FOXFOLK_STEEL
        item_type = Item.ItemTypes.SWORD

        # Sword is NOT in the pool (CraftableItemEntry)
        card_in_hand = Card.objects.create(game=self.game, card_type=card_type.name)
        hand_entry = HandEntry.objects.create(player=self.player, card=card_in_hand)

        with self.assertRaises(ValueError) as cm:
            craft_card(hand_entry, [])
        self.assertEqual(str(cm.exception), "item is not in the craftable pool")
