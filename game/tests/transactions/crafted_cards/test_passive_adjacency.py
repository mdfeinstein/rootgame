from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, CraftedCardEntry, Card
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory
from game.queries.general import get_adjacent_clearings, validate_legal_move, determine_clearing_rule
from game.queries.wa.supporters import validate_sympathy_spread
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.cats.buildings import Workshop
from game.models.birds.buildings import BirdRoost
from game.models.wa.tokens import WASympathy

class AdjacencyPassivesTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE])
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.wa_player = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)
        
        # Clearings for Autumn map:
        # 1-fox, 2-mouse, 3-fox, 4-rabbit, 5-rabbit, 6-fox, 7-mouse, 8-rabbit, 9-mouse, 10-rabbit, 11-mouse, 12-fox
        # Water connections: 4-7, 7-11, 11-10, 10-5
        self.c4 = Clearing.objects.get(game=self.game, clearing_number=4)
        self.c7 = Clearing.objects.get(game=self.game, clearing_number=7)
        self.c10 = Clearing.objects.get(game=self.game, clearing_number=10)
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        self.c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        self.c12 = Clearing.objects.get(game=self.game, clearing_number=12)

    def test_boat_builders_adjacency(self):
        """Test that Boat Builders allows river adjacency."""
        # Baseline: 4 and 7 are connected by river but not path
        self.assertNotIn(self.c7, self.c4.connected_clearings.all())
        self.assertIn(self.c7, self.c4.water_connected_clearings.all())
        
        # Player without Boat Builders
        adj = get_adjacent_clearings(self.cats_player, self.c4)
        self.assertNotIn(self.c7, adj)
        
        # Give Cats Boat Builders
        card = Card.objects.filter(game=self.game, card_type=CardsEP.BOAT_BUILDERS.name).first()
        CraftedCardEntry.objects.create(player=self.cats_player, card=card)
        
        # Now they should be adjacent
        adj = get_adjacent_clearings(self.cats_player, self.c4)
        self.assertIn(self.c7, adj)

    def test_tunnels_adjacency(self):
        """Test that Tunnels allows adjacency between crafting pieces."""
        # Baseline: 5 and 12 are not adjacent
        self.assertNotIn(self.c12, self.c5.connected_clearings.all())
        
        # Give Cats Tunnels
        card = Card.objects.filter(game=self.game, card_type=CardsEP.TUNNELS.name).first()
        CraftedCardEntry.objects.create(player=self.cats_player, card=card)
        
        # Place workshop in 12 (5 already has one from setup)
        from game.models import BuildingSlot
        slot12 = BuildingSlot.objects.filter(clearing=self.c12).first()
        Workshop.objects.create(player=self.cats_player, building_slot=slot12)
        
        # Now 5 and 12 should be adjacent for Cats
        adj = get_adjacent_clearings(self.cats_player, self.c5)
        self.assertIn(self.c12, adj)
        
        adj_back = get_adjacent_clearings(self.cats_player, self.c12)
        self.assertIn(self.c5, adj_back)

    def test_validate_legal_move_boat_builders(self):
        """Test move validation with Boat Builders."""
        # Origin has warriors
        Warrior.objects.create(player=self.cats_player, clearing=self.c4)
        # Cats rule 4
        # determine_clearing_rule return player or None
        # We need to make sure Cats rule at least one
        
        # Give Cats Boat Builders
        card = Card.objects.filter(game=self.game, card_type=CardsEP.BOAT_BUILDERS.name).first()
        CraftedCardEntry.objects.create(player=self.cats_player, card=card)
        
        # Should be able to move 4 -> 7
        try:
            validate_legal_move(self.cats_player, self.c4, self.c7)
        except ValueError as e:
            self.fail(f"validate_legal_move raised ValueError unexpectedly: {e}")

    def test_sympathy_spread_tunnels(self):
        """Test that WA can spread sympathy using Tunnels."""
        # Place sympathy in 1
        WASympathy.objects.create(player=self.wa_player, clearing=self.c1)
        
        # Target clearing 12 (opposite corner)
        # Give WA Tunnels
        card = Card.objects.filter(game=self.game, card_type=CardsEP.TUNNELS.name).first()
        CraftedCardEntry.objects.create(player=self.wa_player, card=card)
        
        # Place another crafting piece in 12 (e.g. sympathy, though sympathy itself is the piece)
        # Actually sympathy IS the crafting piece for WA.
        # So we need a piece in 12 to make it adjacent to 1? 
        # Wait, get_adjacent_clearings(wa, c1) will add c12 IF c12 has a crafting piece.
        # So if we want to spread TO 12, it must already have a piece? 
        # "You treat clearings with any of your crafting pieces as adjacent."
        # If I spread TO a clearing, it doesn't have a piece yet.
        # But if 12 has a BASE (which is not a crafting piece in game_data but maybe should be?), 
        # No, bases are not crafting pieces.
        
        # Let's say WA has a sympathy in 1 and a sympathy in 12 already.
        # Now they want to spread to a clearing adjacent to 12.
        # Clearing 7 is adjacent to 12? No.
        # Let's use 1 and 2. They are adjacent by path.
        # Let's use 1 and 12 again. 12 is adjacent to 11.
        c11 = Clearing.objects.get(game=self.game, clearing_number=11)
        # 1 is NOT adjacent to 11. 11 is adjacent to 12.
        self.assertNotIn(c11, self.c1.connected_clearings.all())
        
        # If WA has sympathy in 1 and 12, and Tunnels:
        # get_adjacent(wa, 1) includes 12.
        # So it SHOULD be possible to spread to 12 (if it didn't have sympathy) if it were adjacent to 1.
        # But to have the TUNNEL, 12 needs a piece.
        
        # This means Tunnels helps spreading FROM a distant piece to ITS neighbors.
        # If I have sympathy in 1, and I have a Workshop in 12 (somehow, maybe through a card effect or just for test),
        # Then 1 is adjacent to 12.
        # So I can spread from 1 TO 12.
        
        # Let's test: WA has sympathy in 1. WA has a Workshop in 12.
        WASympathy.objects.create(player=self.wa_player, clearing=self.c1)
        from game.models import BuildingSlot
        slot12 = BuildingSlot.objects.filter(clearing=self.c12).first()
        Workshop.objects.create(player=self.wa_player, building_slot=slot12)
        
        # Give WA Tunnels
        card = Card.objects.filter(game=self.game, card_type=CardsEP.TUNNELS.name).first()
        CraftedCardEntry.objects.create(player=self.wa_player, card=card)
        
        # Now sympathy in 1 should allow spreading to 12? 
        # wait, validate_sympathy_spread checks if clearing 12 is adjacent to any on-board sympathy.
        # get_adjacent_clearings(wa, c1) includes c12.
        # So it should be valid.
        
        from game.models.wa.player import SupporterStackEntry
        for _ in range(5):
             SupporterStackEntry.objects.create(player=self.wa_player, card=Card.objects.filter(game=self.game).first())

        try:
            validate_sympathy_spread(self.wa_player, self.c12)
        except ValueError as e:
            self.fail(f"validate_sympathy_spread raised ValueError unexpectedly: {e}")

    def test_corvid_planners_movement(self):
        """Test that Corvid Planners allows moving without ruling clearings."""
        self.c11 = Clearing.objects.get(game=self.game, clearing_number=11)
        self.c12 = Clearing.objects.get(game=self.game, clearing_number=12)
        
        # Clear any existing pieces
        Warrior.objects.filter(clearing__in=[self.c11, self.c12]).delete()
        
        # Place 1 Bird in both clearings. Birds rule both (even if tied).
        Warrior.objects.create(player=self.birds_player, clearing=self.c11)
        Warrior.objects.create(player=self.birds_player, clearing=self.c12)
        
        # Place 1 Cat warrior in 11 (origin)
        Warrior.objects.create(player=self.cats_player, clearing=self.c11)
        
        # Verify Cats do NOT rule either (Birds rule due to tie-break)
        self.assertEqual(determine_clearing_rule(self.c11), self.birds_player)
        self.assertEqual(determine_clearing_rule(self.c12), self.birds_player)
        
        # Move should fail
        with self.assertRaises(ValueError):
            validate_legal_move(self.cats_player, self.c11, self.c12)
        
        # Give Cats Corvid Planners
        card = Card.objects.filter(game=self.game, card_type=CardsEP.CORVID_PLANNERS.name).first()
        CraftedCardEntry.objects.create(player=self.cats_player, card=card)
        
        # Now move should succeed
        try:
            validate_legal_move(self.cats_player, self.c11, self.c12)
        except ValueError as e:
            self.fail(f"validate_legal_move raised ValueError unexpectedly: {e}")

    def test_soup_kitchens_rule(self):
        """Test that Soup Kitchens makes tokens count twice for rule."""
        # Clearing 11 is empty. 
        self.c11 = Clearing.objects.get(game=self.game, clearing_number=11)
        
        # Place 1 Cat Wood (Token) and 1 Bird Warrior
        from game.models.cats.tokens import CatWood
        CatWood.objects.create(player=self.cats_player, clearing=self.c11)
        Warrior.objects.create(player=self.birds_player, clearing=self.c11)
        
        # Baseline: Birds rule because tokens don't count
        self.assertEqual(determine_clearing_rule(self.c11), self.birds_player)
        
        # Give Cats Soup Kitchens
        card = Card.objects.filter(game=self.game, card_type=CardsEP.SOUP_KITCHENS.name).first()
        CraftedCardEntry.objects.create(player=self.cats_player, card=card)
        
        # Now wood (token) counts as 2. Cats (2) > Birds (1).
        # Cats should rule.
        self.assertEqual(determine_clearing_rule(self.c11), self.cats_player)
