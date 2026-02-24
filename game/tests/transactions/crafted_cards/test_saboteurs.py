from django.test import TestCase
from game.models.game_models import Faction, CraftedCardEntry, DiscardPileEntry
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.crafted_cards.saboteurs import use_saboteurs
from game.tests.my_factories import (
    GameSetupFactory, BirdTurnFactory, CardFactory, CraftedCardEntryFactory
)

class TestSaboteursTransaction(TestCase):
    def setUp(self):
        # Create a game with Birds and Cats
        self.game = GameSetupFactory(factions=[Faction.BIRDS, Faction.CATS])
        self.player = self.game.players.get(faction=Faction.BIRDS)
        self.opponent = self.game.players.get(faction=Faction.CATS)
        
        # Setup Saboteurs for player
        self.saboteurs_card = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name)
        self.crafted_saboteurs = CraftedCardEntryFactory(
            player=self.player,
            card=self.saboteurs_card,
            used=CraftedCardEntry.UsedChoice.NOT_APPLICABLE # Saboteurs is a discard effect, usually not used/unused but NOT_APPLICABLE?
            # Actually can_use_card checks card_entry.used == USED. 
            # In factories.py, CraftedCardEntryFactory defaults to UNUSED.
        )
        self.crafted_saboteurs.used = CraftedCardEntry.UsedChoice.UNUSED
        self.crafted_saboteurs.save()
        
        # Setup a crafted card for opponent to target
        self.target_card = CardFactory(game=self.game, card_type=CardsEP.FOXFOLK_STEEL.name)
        self.crafted_target = CraftedCardEntryFactory(
            player=self.opponent,
            card=self.target_card,
            used=CraftedCardEntry.UsedChoice.NOT_APPLICABLE
        )

    def test_use_saboteurs_success(self):
        # Move to start of Birdsong for Birds
        self.turn = BirdTurnFactory(player=self.player, turn_number=1)
        from game.models.birds.turn import BirdBirdsong
        birdsong = BirdBirdsong.objects.filter(turn=self.turn).first()
        birdsong.step = "1" # Start of Birdsong
        birdsong.save()
        
        # Transaction
        use_saboteurs(self.player, self.crafted_target)
        
        # Verify effects
        # 1. Saboteurs removed and in discard
        self.assertFalse(CraftedCardEntry.objects.filter(pk=self.crafted_saboteurs.pk).exists())
        self.assertTrue(DiscardPileEntry.objects.filter(card=self.saboteurs_card).exists())
        
        # 2. Target removed and in discard 
        self.assertFalse(CraftedCardEntry.objects.filter(pk=self.crafted_target.pk).exists())
        self.assertTrue(DiscardPileEntry.objects.filter(card=self.target_card).exists())

    def test_use_saboteurs_wrong_phase(self):
        # Move to Daylight
        self.turn = BirdTurnFactory(player=self.player, turn_number=1)
        from game.models.birds.turn import BirdBirdsong, BirdDaylight
        BirdBirdsong.objects.filter(turn=self.turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=self.turn).update(step=BirdDaylight.BirdDaylightSteps.CRAFTING)
        
        with self.assertRaisesMessage(ValueError, "Saboteurs cannot be used right now"):
            use_saboteurs(self.player, self.crafted_target)

    def test_use_saboteurs_target_own_card(self):
        # Setup another card for player
        own_card = CardFactory(game=self.game, card_type=CardsEP.MOUSE_PARTISANS.name)
        crafted_own = CraftedCardEntryFactory(player=self.player, card=own_card)
        
        self.turn = BirdTurnFactory(player=self.player, turn_number=1)
        from game.models.birds.turn import BirdBirdsong
        BirdBirdsong.objects.filter(turn=self.turn).update(step="1")
        
        with self.assertRaisesMessage(ValueError, "You cannot discard your own crafted card"):
             use_saboteurs(self.player, crafted_own)
