from django.test import TestCase
from django.contrib.auth.models import User
from game.models.game_models import Game, Player, Faction, CraftedCardEntry, Card, Suit
from game.models.birds.turn import BirdTurn, BirdBirdsong, BirdDaylight, BirdEvening
from game.models.cats.turn import CatTurn, CatBirdsong, CatDaylight, CatEvening
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.cards.active_effects import can_use_card

class ActiveEffectsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")
        self.game = Game.objects.create(owner=self.user)
        self.player_birds = Player.objects.create(game=self.game, faction=Faction.BIRDS, user=self.user, turn_order=0)
        self.turn = BirdTurn.create_turn(self.player_birds)
        
        # Setup Cats
        self.user2 = User.objects.create(username="testuser2")
        self.player_cats = Player.objects.create(game=self.game, faction=Faction.CATS, user=self.user2, turn_order=1)
        self.turn_cats = CatTurn.create_turn(self.player_cats)

        # Create Dummy Cards in DB required for CraftedCardEntry
        # We need to ensure Card objects exist for the enums we test
        self.card_saboteurs = self.create_card_object(CardsEP.SABOTEURS)
        self.card_propaganda = self.create_card_object(CardsEP.PROPAGANDA_BUREAU)
        self.card_informants = self.create_card_object(CardsEP.INFORMANTS)
        self.card_charm = self.create_card_object(CardsEP.CHARM_OFFENSIVE)

    def create_card_object(self, card_enum):
        return Card.objects.create(
            game=self.game,
            card_type=card_enum.name,
            suit=Suit.WILD # Suit doesn't matter for this test context usually, but required field
        )

    def test_saboteurs_timing_birds(self):
        # Crafted Card
        entry = CraftedCardEntry.objects.create(player=self.player_birds, card=self.card_saboteurs)
        
        # 1. Correct Timing: Birdsong, Emergency Drawing
        birdsong = self.turn.birdsong.first()
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.EMERGENCY_DRAWING
        birdsong.save()
        self.assertTrue(can_use_card(self.player_birds, entry))

        # 2. Incorrect Timing: Birdsong, Add to Decree
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE
        birdsong.save()
        self.assertFalse(can_use_card(self.player_birds, entry))

        # 3. Incorrect Phase: Daylight
        self.assertFalse(can_use_card(self.player_birds, entry)) # Implicitly checks active phase logic

    def test_propaganda_bureau_timing_birds(self):
        entry = CraftedCardEntry.objects.create(player=self.player_birds, card=self.card_propaganda)
        
        # Daylight
        # Must complete Birdsong first
        birdsong = self.turn.birdsong.first()
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()
        
        # Now get_phase should return Daylight
        self.assertTrue(can_use_card(self.player_birds, entry))

    def test_informants_timing_birds(self):
        entry = CraftedCardEntry.objects.create(player=self.player_birds, card=self.card_informants)
        
        # Need Evening, Drawing step
        # Complete Birdsong and Daylight
        birdsong = self.turn.birdsong.first()
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()
        
        daylight = self.turn.daylight.first()
        daylight.step = BirdDaylight.BirdDaylightSteps.COMPLETED
        daylight.save()
        
        evening = self.turn.evening.first()
        evening.step = BirdEvening.BirdEveningSteps.SCORING
        evening.save()
        
        # Scoring is not Drawing. Should be False.
        self.assertFalse(can_use_card(self.player_birds, entry))
        
        # Set to Drawing
        evening.step = BirdEvening.BirdEveningSteps.DRAWING
        evening.save()
        self.assertTrue(can_use_card(self.player_birds, entry))

    def test_cats_timing(self):
        # 1. Saboteurs (Start of Birdsong -> Placing Wood)
        entry_sab = CraftedCardEntry.objects.create(player=self.player_cats, card=self.card_saboteurs)
        
        birdsong = self.turn_cats.birdsong
        birdsong.step = CatBirdsong.CatBirdsongSteps.PLACING_WOOD
        birdsong.save()
        
        # Set game turn to Cats
        self.game.current_turn = 1
        self.game.save()
        
        self.assertTrue(can_use_card(self.player_cats, entry_sab))
        
        # Advance Step (Wait, only 1 step in Cat Birdsong before Completed?)
        # Let's Mark Completed -> Daylight
        birdsong.step = CatBirdsong.CatBirdsongSteps.COMPLETED
        birdsong.save()
        self.assertFalse(can_use_card(self.player_cats, entry_sab))
        
        # 2. Propaganda Bureau (Daylight)
        entry_prop = CraftedCardEntry.objects.create(player=self.player_cats, card=self.card_propaganda)
        # Should be Daylight now
        self.assertTrue(can_use_card(self.player_cats, entry_prop))
        
        # 3. Informants (Evening, Drawing)
        entry_inf = CraftedCardEntry.objects.create(player=self.player_cats, card=self.card_informants)
        daylight = self.turn_cats.daylight
        daylight.step = CatDaylight.CatDaylightSteps.COMPLETED
        daylight.save()
        
        evening = self.turn_cats.evening
        evening.step = CatEvening.CatEveningSteps.DRAWING
        evening.save()
        self.assertTrue(can_use_card(self.player_cats, entry_inf))
        
        # Advance to Discarding
        evening.step = CatEvening.CatEveningSteps.DISCARDING
        evening.save()
        self.assertFalse(can_use_card(self.player_cats, entry_inf))

    def test_used_card(self):
        entry = CraftedCardEntry.objects.create(player=self.player_birds, card=self.card_propaganda, used=CraftedCardEntry.UsedChoice.USED)
        # Even if timing is right (Daylight)
        birdsong = self.turn.birdsong.first()
        birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        birdsong.save()
        
        self.assertFalse(can_use_card(self.player_birds, entry))
