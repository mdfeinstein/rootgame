from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior, HandEntry, Suit
from game.models.birds.buildings import BirdRoost
from game.models.birds.player import BirdLeader, DecreeEntry, Vizier
from game.models.birds.turn import BirdTurn, BirdBirdsong
from game.tests.my_factories import GameSetupFactory, CardFactory, HandEntryFactory
from game.transactions.birds import emergency_draw, add_card_to_decree, end_add_to_decree_step, emergency_roost, try_auto_emergency_roost
from game.game_data.cards.exiles_and_partisans import CardsEP

class BirdBirdsongBaseTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Set current player to Birds
        self.game.current_turn = self.player.turn_order
        self.game.save()
        
        # Create a turn for Birds
        self.turn = BirdTurn.create_turn(self.player)
        self.birdsong = self.turn.birdsong.first()
        self.birdsong.step = BirdBirdsong.BirdBirdsongSteps.EMERGENCY_DRAWING
        self.birdsong.save()

class BirdEmergencyDrawTests(BirdBirdsongBaseTestCase):
    def test_emergency_draw_when_empty(self):
        # Empty hand
        HandEntry.objects.filter(player=self.player).delete()
        
        emergency_draw(self.player)
        
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), 1)
        self.birdsong.refresh_from_db()
        self.assertEqual(self.birdsong.step, BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE)

    def test_no_emergency_draw_when_not_empty(self):
        # Hand with 1 card
        HandEntry.objects.filter(player=self.player).delete()
        HandEntryFactory(player=self.player)
        
        emergency_draw(self.player)
        
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), 1)
        self.birdsong.refresh_from_db()
        self.assertEqual(self.birdsong.step, BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE)

class BirdDecreeTests(BirdBirdsongBaseTestCase):
    def setUp(self):
        super().setUp()
        self.birdsong.step = BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE
        self.birdsong.save()
        
        HandEntry.objects.filter(player=self.player).delete()
        self.card1 = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        self.card2 = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_YELLOW.name)
        self.bird_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_WILD.name)
        
        self.h1 = HandEntry.objects.create(player=self.player, card=self.card1)
        self.h2 = HandEntry.objects.create(player=self.player, card=self.card2)
        self.hb = HandEntry.objects.create(player=self.player, card=self.bird_card)


    def test_add_one_card_to_decree_success(self):
        add_card_to_decree(self.player, CardsEP.AMBUSH_RED, DecreeEntry.Column.RECRUIT)
        
        self.assertTrue(DecreeEntry.objects.filter(player=self.player, column=DecreeEntry.Column.RECRUIT, card=self.card1).exists())
        self.assertFalse(HandEntry.objects.filter(pk=self.h1.pk).exists())
        self.birdsong.refresh_from_db()
        self.assertEqual(self.birdsong.cards_added_to_decree, 1)

    def test_add_two_cards_to_decree_advances_step(self):
        add_card_to_decree(self.player, CardsEP.AMBUSH_RED, DecreeEntry.Column.RECRUIT)
        add_card_to_decree(self.player, CardsEP.AMBUSH_YELLOW, DecreeEntry.Column.MOVE)
        
        self.birdsong.refresh_from_db()
        self.assertEqual(self.birdsong.step, BirdBirdsong.BirdBirdsongSteps.EMERGENCY_ROOSTING)
        self.assertEqual(self.birdsong.cards_added_to_decree, 2)

    def test_add_two_bird_cards_fails(self):
        # First bird card
        add_card_to_decree(self.player, CardsEP.AMBUSH_WILD, DecreeEntry.Column.RECRUIT)
        
        # Second bird card
        bird_card_2 = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name) # Saboteurs is Wild (Bird)
        HandEntry.objects.create(player=self.player, card=bird_card_2)
        
        with self.assertRaisesMessage(ValueError, "Bird card already added to decree"):
            add_card_to_decree(self.player, CardsEP.SABOTEURS, DecreeEntry.Column.MOVE)

    def test_add_three_cards_fails(self):
        add_card_to_decree(self.player, CardsEP.AMBUSH_RED, DecreeEntry.Column.RECRUIT)
        add_card_to_decree(self.player, CardsEP.AMBUSH_YELLOW, DecreeEntry.Column.MOVE)
        
        # Manually reset step to test the transaction guard
        self.birdsong.refresh_from_db()
        self.birdsong.step = BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE
        self.birdsong.save()
        
        c3 = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_ORANGE.name)
        HandEntry.objects.create(player=self.player, card=c3)
        
        with self.assertRaisesMessage(ValueError, "Two cards already added to decree"):
             add_card_to_decree(self.player, CardsEP.AMBUSH_ORANGE, DecreeEntry.Column.BATTLE)


    def test_end_add_to_decree_with_zero_cards_fails(self):
        with self.assertRaisesMessage(ValueError, "Must add at least one card to decree"):
            end_add_to_decree_step(self.player)



class BirdEmergencyRoostTests(BirdBirdsongBaseTestCase):
    def setUp(self):
        super().setUp()
        self.birdsong.step = BirdBirdsong.BirdBirdsongSteps.EMERGENCY_ROOSTING
        self.birdsong.save()

    def test_emergency_roost_success(self):
        # Remove all roosts from board
        BirdRoost.objects.filter(player=self.player).update(building_slot=None)
        
        # Clearing with 0 warriors (C5, C6 etc)
        c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        Warrior.objects.filter(clearing=c5).delete()
        
        emergency_roost(self.player, c5)
        
        self.assertTrue(BirdRoost.objects.filter(player=self.player, building_slot__clearing=c5).exists())
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=c5).count(), 3)
        self.birdsong.refresh_from_db()
        self.assertEqual(self.birdsong.step, BirdBirdsong.BirdBirdsongSteps.COMPLETED)

    def test_emergency_roost_not_fewest_warriors_fails(self):
        BirdRoost.objects.filter(player=self.player).update(building_slot=None)
        
        # C5 has 0 warriors
        c5 = Clearing.objects.get(game=self.game, clearing_number=5)
        Warrior.objects.filter(clearing=c5).delete()
        
        # C1 has some warriors (placed by cats factories usually, but let's be sure)
        c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        Warrior.objects.create(player=self.cats_player, clearing=c1)
        
        with self.assertRaisesMessage(ValueError, "Chosen clearing does not have the fewest total warriors"):
            emergency_roost(self.player, c1)

    def test_try_auto_emergency_roost_unique_best(self):
        BirdRoost.objects.filter(player=self.player).update(building_slot=None)
        
        # Make C10 the only clearing with 0 warriors, others have 1
        for c in Clearing.objects.filter(game=self.game):
            Warrior.objects.filter(clearing=c).delete()
            if c.clearing_number != 10:
                Warrior.objects.create(player=self.cats_player, clearing=c)
        
        c10 = Clearing.objects.get(game=self.game, clearing_number=10)
        try_auto_emergency_roost(self.player)
        
        self.assertTrue(BirdRoost.objects.filter(player=self.player, building_slot__clearing=c10).exists())
        self.birdsong.refresh_from_db()
        self.assertEqual(self.birdsong.step, BirdBirdsong.BirdBirdsongSteps.COMPLETED)
