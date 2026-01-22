from django.test import TestCase
from game.models.game_models import Faction, CraftedCardEntry
from game.models.birds.turn import BirdEvening
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.crafted_cards.charm_offensive import use_charm_offensive
from game.tests.my_factories import (
    GameSetupFactory, BirdTurnFactory, CardFactory, CraftedCardEntryFactory
)

class TestCharmOffensiveTransaction(TestCase):
    def setUp(self):
        # Create a game with Birds and Cats
        self.game = GameSetupFactory(factions=[Faction.BIRDS, Faction.CATS])
        self.player = self.game.players.get(faction=Faction.BIRDS)
        self.opponent = self.game.players.get(faction=Faction.CATS)
        
        # Setup Charm Offensive card
        self.charm_card = CardFactory(game=self.game, card_type=CardsEP.CHARM_OFFENSIVE.name)
        self.crafted_charm = CraftedCardEntryFactory(
            player=self.player,
            card=self.charm_card,
            used=CraftedCardEntry.UsedChoice.UNUSED
        )

    def test_use_charm_offensive_success(self):
        # Move to start of Evening for Birds
        self.turn = BirdTurnFactory(player=self.player, turn_number=1)
        
        from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening
        
        BirdBirdsong.objects.filter(turn=self.turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=self.turn).update(step=BirdDaylight.BirdDaylightSteps.COMPLETED)
        evening = BirdEvening.objects.filter(turn=self.turn).first()
        evening.step = BirdEvening.BirdEveningSteps.SCORING # "1" (Start of Evening)
        evening.save()
        
        from game.queries.general import get_player_hand_size
        initial_score = self.opponent.score
        initial_hand_size = get_player_hand_size(self.player)
        
        # Transaction
        use_charm_offensive(self.player, self.opponent)
        
        # Verify effects
        self.opponent.refresh_from_db()
        self.crafted_charm.refresh_from_db()
        
        self.assertEqual(self.opponent.score, initial_score + 1)
        self.assertEqual(get_player_hand_size(self.player), initial_hand_size + 1)
        self.assertEqual(self.crafted_charm.used, CraftedCardEntry.UsedChoice.USED)

    def test_use_charm_offensive_wrong_phase(self):
        # Move to Daylight
        self.turn = BirdTurnFactory(player=self.player, turn_number=1)
        
        from game.models.birds.turn import BirdBirdsong, BirdDaylight
        BirdBirdsong.objects.filter(turn=self.turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=self.turn).update(step=BirdDaylight.BirdDaylightSteps.CRAFTING)
        
        with self.assertRaisesMessage(ValueError, "Charm Offensive cannot be used right now"):
            use_charm_offensive(self.player, self.opponent)

    def test_use_charm_offensive_already_used(self):
        self.turn = BirdTurnFactory(player=self.player, turn_number=1)
        
        from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening
        BirdBirdsong.objects.filter(turn=self.turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=self.turn).update(step=BirdDaylight.BirdDaylightSteps.COMPLETED)
        BirdEvening.objects.filter(turn=self.turn).update(step=BirdEvening.BirdEveningSteps.SCORING)
        
        self.crafted_charm.used = CraftedCardEntry.UsedChoice.USED
        self.crafted_charm.save()
        
        with self.assertRaisesMessage(ValueError, "Charm Offensive cannot be used right now"):
            use_charm_offensive(self.player, self.opponent)
