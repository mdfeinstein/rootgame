from django.test import TestCase
from game.models.game_models import Faction, Card, CraftedCardEntry, Clearing, Suit, Warrior, CoffinWarrior
from game.models.cats.turn import CatTurn, CatBirdsong
from game.models.events.battle import Battle
from game.models.events.event import Event, EventType
from game.tests.my_factories import GameSetupWithFactionsFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.transactions.removal import player_removes_warriors
from game.transactions.cats import cat_resolve_field_hospital
from game.transactions.crafted_cards.coffin_makers import score_coffins, release_warriors
from game.queries.crafted_cards import get_coffin_warriors_count

class CoffinMakersTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE])
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.wa_player = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)
        
        # Give Birds Coffin Makers
        card_cm = Card.objects.filter(game=self.game, card_type=CardsEP.COFFIN_MAKERS.name).first()
        self.cm_entry = CraftedCardEntry.objects.create(player=self.birds_player, card=card_cm)
        
        self.fox_clearing = Clearing.objects.filter(game=self.game, suit=Suit.RED).first()
        
        # Clear supply for all players to make tests deterministic
        Warrior.objects.filter(player__game=self.game).delete()

    def test_coffin_makers_capture_non_cats(self):
        """Test that non-cat warriors go straight to the coffin."""
        # Birds player has Coffin Makers
        # WA player loses 2 warriors in fox clearing
        # (Assuming WA has warriors there from setup, or we add some)
        Warrior.objects.create(player=self.wa_player, clearing=self.fox_clearing)
        Warrior.objects.create(player=self.wa_player, clearing=self.fox_clearing)
        
        player_removes_warriors(self.fox_clearing, self.birds_player, self.wa_player, 2)
        
        # Verify they are in the coffin
        self.assertEqual(get_coffin_warriors_count(self.game), 2)
        self.assertEqual(Warrior.objects.filter(player=self.wa_player, clearing=self.fox_clearing).count(), 0)
        self.assertEqual(Warrior.objects.filter(player=self.wa_player, clearing=None).count(), 0) # Should be deleted and replaced by CoffinWarrior

    def test_coffin_makers_cats_field_hospital_interaction(self):
        """Test that Cats can save warriors before they go to the coffin."""
        # Cats lose 2 warriors
        Warrior.objects.create(player=self.cats_player, clearing=self.fox_clearing)
        Warrior.objects.create(player=self.cats_player, clearing=self.fox_clearing)
        
        player_removes_warriors(self.fox_clearing, self.birds_player, self.cats_player, 2)
        
        # At this point, warriors should be in clearing=None (supply) but NOT yet in coffin
        self.assertEqual(get_coffin_warriors_count(self.game), 0)
        self.assertEqual(Warrior.objects.filter(player=self.cats_player, clearing=None).count(), 2)
        
        # Resolve field hospital - skip saving
        cat_resolve_field_hospital(self.cats_player, None)
        
        # Now they should be in the coffin
        self.assertEqual(get_coffin_warriors_count(self.game), 2)
        self.assertEqual(Warrior.objects.filter(player=self.cats_player, clearing=None).count(), 0)

    def test_coffin_makers_scoring_rounds_down(self):
        """Test that scoring at Birdsong rounds down (1 VP per 5 warriors)."""
        # Put 9 warriors in the coffin
        for _ in range(9):
            CoffinWarrior.objects.create(player=self.wa_player)
            
        initial_score = self.birds_player.score
        score_coffins(self.birds_player)
        
        # 9 // 5 = 1 VP
        self.assertEqual(self.birds_player.score, initial_score + 1)
        
        # Add 1 more for a total of 10
        CoffinWarrior.objects.create(player=self.wa_player)
        score_coffins(self.birds_player)
        
        # 10 // 5 = 2 VP. total score = 1 + 2 = 3
        self.assertEqual(self.birds_player.score, initial_score + 3)

    def test_coffin_makers_release(self):
        """Test that warriors return to their owners' supply when released."""
        # Mix of warriors
        CoffinWarrior.objects.create(player=self.cats_player)
        CoffinWarrior.objects.create(player=self.wa_player)
        
        release_warriors(self.game)
        
        self.assertEqual(get_coffin_warriors_count(self.game), 0)
        # Verify they exist in supply (clearing=None)
        self.assertTrue(Warrior.objects.filter(player=self.cats_player, clearing=None).exists())
        self.assertTrue(Warrior.objects.filter(player=self.wa_player, clearing=None).exists())

    def test_sabotaged_coffin_makers_release_warriors(self):
        """Test that warriors return to their owners' supply when coffin makers is sabotaged.
        Also check that no points are scored by coffin maker player.
        """
        from game.transactions.crafted_cards.saboteurs import use_saboteurs
        from game.models.events.crafted_cards import SaboteursEvent

        # 1. Give Cats Saboteurs
        card_sab = Card.objects.filter(game=self.game, card_type=CardsEP.SABOTEURS.name).first()
        sab_entry = CraftedCardEntry.objects.create(player=self.cats_player, card=card_sab)
        # Create the event since use_saboteurs expects it
        SaboteursEvent.create(sab_entry)
        
        # Ensure Cats are at start of Birdsong
        cat_turn = CatTurn.objects.filter(player=self.cats_player).first()
        if not cat_turn:
            cat_turn = CatTurn.create_turn(self.cats_player)
        birdsong = cat_turn.birdsong
        birdsong.step = CatBirdsong.CatBirdsongSteps.PLACING_WOOD
        birdsong.save()
        
        # 2. Put 5 warriors in the coffin (enough for 1 point)
        for _ in range(5):
             CoffinWarrior.objects.create(player=self.wa_player)
             
        # 3. Use Saboteurs on Birds' Coffin Makers
        initial_bird_score = self.birds_player.score
        use_saboteurs(self.cats_player, self.cm_entry)
        
        # 4. Verify warriors are released
        self.assertEqual(get_coffin_warriors_count(self.game), 0)
        self.assertEqual(Warrior.objects.filter(player=self.wa_player, clearing=None).count(), 5)
        
        # 5. Verify Coffin Makers is gone
        self.assertFalse(CraftedCardEntry.objects.filter(id=self.cm_entry.id).exists())
        
        # 6. Verify Birds score (should be unchanged)
        self.assertEqual(self.birds_player.score, initial_bird_score)
