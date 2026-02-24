from django.test import TestCase
from game.models.game_models import Faction, CraftedCardEntry, Clearing
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.crafted_cards.league_of_adventurers import use_league_of_adventurers
from game.tests.my_factories import (
    GameSetupFactory, BirdTurnFactory, CardFactory, CraftedCardEntryFactory,
    CraftedItemEntryFactory, WarriorFactory
)

class TestLeagueOfAdventurersTransaction(TestCase):
    def setUp(self):
        # Create a game with Birds and Cats
        self.game = GameSetupFactory(factions=[Faction.BIRDS, Faction.CATS])
        self.player = self.game.players.get(faction=Faction.BIRDS)
        self.opponent = self.game.players.get(faction=Faction.CATS)
        
        # Setup League of Adventurers card
        self.league_card = CardFactory(game=self.game, card_type=CardsEP.LEAGUE_OF_ADVENTURERS.name)
        self.crafted_league = CraftedCardEntryFactory(
            player=self.player,
            card=self.league_card,
            used=CraftedCardEntry.UsedChoice.UNUSED
        )
        
        # Setup an item to exhaust
        self.crafted_item = CraftedItemEntryFactory(player=self.player)
        
        # Initial turn setup (Daylight)
        self.turn = BirdTurnFactory(player=self.player, turn_number=1)
        from game.models.birds.turn import BirdBirdsong, BirdDaylight
        BirdBirdsong.objects.filter(turn=self.turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=self.turn).update(step=BirdDaylight.BirdDaylightSteps.CRAFTING)

    def test_use_league_of_adventurers_move_success(self):
        # Setup clearings and warriors
        clearing1 = Clearing.objects.get(game=self.game, clearing_number=1)
        clearing2 = Clearing.objects.get(game=self.game, clearing_number=2)
        # Ensure they are adjacent (Autumn map 1-2 is adjacent)
        clearing1.connected_clearings.add(clearing2)
        
        WarriorFactory.create_batch(3, player=self.player, clearing=clearing1)
        
        move_data = {
            "origin_clearing": clearing1,
            "target_clearing": clearing2,
            "number": 2
        }
        
        use_league_of_adventurers(self.crafted_league, self.crafted_item, move_data=move_data)
        
        # Verify effects
        from game.models.game_models import Warrior
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=clearing1).count(), 1)
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=clearing2).count(), 2)
        
        self.crafted_item.refresh_from_db()
        self.assertTrue(self.crafted_item.exhausted)
        
        self.crafted_league.refresh_from_db()
        self.assertEqual(self.crafted_league.used, CraftedCardEntry.UsedChoice.USED)

    def test_use_league_of_adventurers_battle_success(self):
        # Setup clearing and warriors for battle
        clearing1 = Clearing.objects.get(game=self.game, clearing_number=1)
        WarriorFactory(player=self.player, clearing=clearing1)
        WarriorFactory(player=self.opponent, clearing=clearing1)
        
        battle_data = {
            "clearing": clearing1,
            "opponent_faction": self.opponent.faction
        }
        
        use_league_of_adventurers(self.crafted_league, self.crafted_item, battle_data=battle_data)
        
        # Verify battle was started
        from game.models.events.battle import Battle
        self.assertTrue(Battle.objects.filter(clearing=clearing1, attacker=self.player.faction, defender=self.opponent.faction).exists())
        
        self.crafted_item.refresh_from_db()
        self.assertTrue(self.crafted_item.exhausted)
        
        self.crafted_league.refresh_from_db()
        self.assertEqual(self.crafted_league.used, CraftedCardEntry.UsedChoice.USED)

    def test_fails_if_item_already_exhausted(self):
        self.crafted_item.exhausted = True
        self.crafted_item.save()
        
        clearing1 = Clearing.objects.get(game=self.game, clearing_number=1)
        clearing2 = Clearing.objects.get(game=self.game, clearing_number=2)
        clearing1.connected_clearings.add(clearing2)
        WarriorFactory.create_batch(1, player=self.player, clearing=clearing1)
        
        move_data = {"origin_clearing": clearing1, "target_clearing": clearing2, "number": 1}
        
        with self.assertRaisesMessage(ValueError, "This item is already exhausted"):
            use_league_of_adventurers(self.crafted_league, self.crafted_item, move_data=move_data)

    def test_fails_if_wrong_phase(self):
        # Move to Evening
        from game.models.birds.turn import BirdDaylight, BirdEvening
        BirdDaylight.objects.filter(turn=self.turn).update(step=BirdDaylight.BirdDaylightSteps.COMPLETED)
        BirdEvening.objects.filter(turn=self.turn).update(step=BirdEvening.BirdEveningSteps.SCORING)
        
        clearing1 = Clearing.objects.get(game=self.game, clearing_number=1)
        clearing2 = Clearing.objects.get(game=self.game, clearing_number=2)
        clearing1.connected_clearings.add(clearing2)
        WarriorFactory.create_batch(1, player=self.player, clearing=clearing1)
        
        move_data = {"origin_clearing": clearing1, "target_clearing": clearing2, "number": 1}
        
        with self.assertRaisesMessage(ValueError, "League of Adventurers cannot be used right now"):
            use_league_of_adventurers(self.crafted_league, self.crafted_item, move_data=move_data)
