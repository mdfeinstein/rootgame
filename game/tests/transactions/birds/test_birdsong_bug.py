from django.test import TestCase
from game.models.game_models import Faction, HandEntry
from game.models.birds.player import DecreeEntry
from game.models.birds.turn import BirdTurn, BirdBirdsong
from game.tests.my_factories import GameSetupFactory, CardFactory
from game.transactions.birds import add_card_to_decree
from game.game_data.cards.exiles_and_partisans import CardsEP

class BirdDecreeBugTest(TestCase):
    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.CATS, Faction.BIRDS])
        self.player = self.game.players.get(faction=Faction.BIRDS)
        
        # Set current player to Birds
        self.game.current_turn = self.player.turn_order
        self.game.save()
        
        # Create a turn for Birds
        self.turn = BirdTurn.create_turn(self.player)
        self.birdsong = self.turn.birdsong.first()
        self.birdsong.step = BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE
        self.birdsong.save()
        
        HandEntry.objects.filter(player=self.player).delete()
        self.red_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        self.bird_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_WILD.name)
        
        self.h1 = HandEntry.objects.create(player=self.player, card=self.red_card)
        self.h2 = HandEntry.objects.create(player=self.player, card=self.bird_card)

    def test_reproduce_not_moving_step_error(self):
        # Force exactly one clearing to have the fewest warriors (0 warriors vs >=1)
        # to trigger try_auto_emergency_roost's unique clearing resolution logic
        from game.models.game_models import Clearing, Warrior
        
        # Give all clearings 1 warrior initially
        clearings = Clearing.objects.filter(game=self.game)
        for clearing in clearings:
            if Warrior.objects.filter(clearing=clearing, player=self.player).count() == 0:
                Warrior.objects.create(player=self.player, clearing=clearing)
                
        # Make exactly ONE clearing have 0 warriors
        first_clearing = clearings.first()
        Warrior.objects.filter(clearing=first_clearing).delete()
        
        # ensure there is a roost
        from game.models.birds.buildings import BirdRoost
        roost = BirdRoost.objects.filter(player=self.player).first()
        from game.models import BuildingSlot
        # Just stick it anywhere, for testing
        roost.building_slot = BuildingSlot.objects.filter(clearing=first_clearing).first()
        roost.save()

        # Adding a red card first
        add_card_to_decree(self.player, CardsEP.AMBUSH_RED, DecreeEntry.Column.RECRUIT)
        
        # Adding a bird card second shouldn't throw "Not Moving Step"
        add_card_to_decree(self.player, CardsEP.AMBUSH_WILD, DecreeEntry.Column.BUILD)
