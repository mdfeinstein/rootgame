from django.test import TestCase
from django.contrib.auth.models import User
from game.models.game_models import Game, Player, Faction, Card, CraftedCardEntry, Warrior, Clearing, Suit, HandEntry
from game.models.birds.turn import BirdTurn, BirdBirdsong, BirdDaylight, BirdEvening
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.crafted_cards.propaganda_bureau import use_propaganda_bureau

from game.tests.my_factories import (
    GameFactory, PlayerFactory, BirdTurnFactory, CardFactory, 
    CraftedCardEntryFactory, HandEntryFactory, ClearingFactory, WarriorFactory
)

class TestPropagandaBureauTransaction(TestCase):
    def setUp(self):
        self.game = GameFactory()
        self.player = PlayerFactory(game=self.game, faction=Faction.BIRDS, turn_order=0)
        
        # Phase setup - Daylight for PB usage
        # BirdTurnFactory creates phases by default (via create_turn)
        self.bird_turn = BirdTurnFactory(player=self.player, turn_number=1)
        
        from game.models.birds.turn import BirdBirdsong, BirdDaylight
        birdsong = BirdBirdsong.objects.filter(turn=self.bird_turn).first()
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()
        self.daylight = BirdDaylight.objects.filter(turn=self.bird_turn).first()
        self.daylight.step = "1" # Daylight active
        self.daylight.save()

        # Cards
        self.pb_card = CardFactory(game=self.game, card_type=CardsEP.PROPAGANDA_BUREAU.name)
        # Use a real card that has a suit, e.g. FOXFOLK_STEEL (Fox suit)
        self.fox_card = CardFactory(game=self.game, card_type=CardsEP.FOXFOLK_STEEL.name) 
        
        # Crafted PB
        self.crafted_pb = CraftedCardEntryFactory(
            player=self.player,
            card=self.pb_card,
            used=CraftedCardEntry.UsedChoice.UNUSED
        )
        
        # Hand
        self.hand_entry = HandEntryFactory(player=self.player, card=self.fox_card)
        
        # Board Setup
        self.clearing_fox = ClearingFactory(game=self.game, suit=Suit.RED, clearing_number=1)
        
        # Enemy (Cats)
        self.cat_player = PlayerFactory(game=self.game, faction=Faction.CATS, turn_order=1)
        self.cat_warrior = WarriorFactory(player=self.cat_player, clearing=self.clearing_fox)
        
        # Player Warrior (in supply)
        self.bird_warrior = WarriorFactory(player=self.player, clearing=None)


    def test_use_propaganda_bureau_success(self):
        card_ep = CardsEP.FOXFOLK_STEEL # Matches fox clearing
        target_faction = Faction.CATS
        
        use_propaganda_bureau(self.player, card_ep, self.clearing_fox, target_faction)
        
        # Verify effects
        self.cat_warrior.refresh_from_db()
        self.bird_warrior.refresh_from_db()
        self.crafted_pb.refresh_from_db()
        
        self.assertIsNone(self.cat_warrior.clearing) # Removed
        self.assertEqual(self.bird_warrior.clearing, self.clearing_fox) # Added
        self.assertEqual(self.crafted_pb.used, CraftedCardEntry.UsedChoice.USED) # Used
        self.assertFalse(HandEntry.objects.filter(player=self.player, card=self.fox_card).exists()) # Discarded

    def test_use_propaganda_bureau_invalid_card_suit(self):
        # Create a mouse clearing
        clearing_mouse = Clearing.objects.create(game=self.game, suit=Suit.ORANGE, clearing_number=2)
        # Add cat warrior there
        Warrior.objects.create(player=self.cat_player, clearing=clearing_mouse)
        
        card_ep = CardsEP.FOXFOLK_STEEL # Fox suit
        target_faction = Faction.CATS
        
        with self.assertRaisesMessage(ValueError, "Card suit does not match clearing suit"):
            use_propaganda_bureau(self.player, card_ep, clearing_mouse, target_faction)

    def test_use_propaganda_bureau_no_enemy(self):
        # Remove cat warrior
        self.cat_warrior.delete()
        
        card_ep = CardsEP.FOXFOLK_STEEL
        target_faction = Faction.CATS
        
        with self.assertRaisesMessage(ValueError, "No enemy warrior found"):
            use_propaganda_bureau(self.player, card_ep, self.clearing_fox, target_faction)

    def test_use_propaganda_bureau_already_used(self):
        self.crafted_pb.used = CraftedCardEntry.UsedChoice.USED
        self.crafted_pb.save()
        
        card_ep = CardsEP.FOXFOLK_STEEL
        target_faction = Faction.CATS
        
        with self.assertRaisesMessage(ValueError, "Propaganda Bureau cannot be used right now"):
            use_propaganda_bureau(self.player, card_ep, self.clearing_fox, target_faction)

    def test_use_propaganda_bureau_wrong_phase(self):
        # Move to evening
        self.daylight.step = BirdDaylight.BirdDaylightSteps.COMPLETED
        self.daylight.save()
        
        card_ep = CardsEP.FOXFOLK_STEEL
        target_faction = Faction.CATS
        
        with self.assertRaisesMessage(ValueError, "Propaganda Bureau cannot be used right now"):
            use_propaganda_bureau(self.player, card_ep, self.clearing_fox, target_faction)
