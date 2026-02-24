import logging
from django.test import TestCase
from game.models import (
    Faction,
    Game,
    Player,
    Clearing,
    HandEntry,
    BirdTurn,
    BirdBirdsong,
    BirdDaylight,
    BirdRoost,
    Suit,
    WarriorSupplyEntry,
    Warrior,
)
from game.models.birds.player import BirdLeader, DecreeEntry, Vizier
from game.tests.my_factories import (
    GameFactory,
    PlayerFactory,
    CardFactory,
    HandEntryFactory,
    GameSetupWithFactionsFactory,
)
from game.transactions.birds import (
    bird_craft_card,
    bird_recruit_action,
    bird_move_action,
    bird_battle_action,
    bird_build_action,
    turmoil,
)
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.birds.turn import get_phase
from django.db import transaction

logger = logging.getLogger(__name__)

class BirdDaylightBaseTestCase(TestCase):
    def setUp(self):
        # Create a game with Cats and Birds
        self.game = GameSetupWithFactionsFactory()
        self.player = self.game.players.get(faction=Faction.BIRDS)
        self.cats_player = self.game.players.get(faction=Faction.CATS)
        
        # Set current turn to Birds
        self.game.current_turn = self.player.turn_order
        self.game.save()
        
        # Create a turn for Birds
        self.turn = BirdTurn.create_turn(self.player)
        
        # Must complete Birdsong for get_phase to return Daylight
        self.birdsong = self.turn.birdsong.first()
        self.birdsong.step = BirdBirdsong.BirdBirdsongSteps.COMPLETED
        self.birdsong.save()
        
        self.daylight = self.turn.daylight.first()
        self.daylight.step = BirdDaylight.BirdDaylightSteps.CRAFTING
        self.daylight.save()

        # Birds start with a roost in clearing 3 (Yellow/Rabbit)
        self.roost3 = BirdRoost.objects.get(player=self.player, building_slot__clearing__clearing_number=3)
        self.clearing3 = self.roost3.building_slot.clearing
        
        # Clear all Viziers to avoid unexpected turmoil during step transitions
        Vizier.objects.filter(player=self.player).delete()
        
        # Add a decree card to each column to prevent auto-turn completion
        for column in DecreeEntry.Column:
            DecreeEntry.objects.create(player=self.player, column=column, card=CardFactory(game=self.game))
            
        # Give player an extra card to prevent auto-turn completion from bird_craft_card
        HandEntry.objects.create(player=self.player, card=CardFactory(game=self.game))

        # Setup clearing 4 with a roost
        self.clearing4 = Clearing.objects.get(game=self.game, clearing_number=4)
        from game.queries.general import available_building_slot
        slot4 = available_building_slot(self.clearing4)
        self.roost4 = BirdRoost.objects.filter(player=self.player, building_slot=None).first()
        self.roost4.building_slot = slot4
        self.roost4.save()
        
        # Place a 3rd roost to prevent auto-turn completion from bird_craft_card (unused_roosts > 0)
        self.clearing5 = Clearing.objects.get(game=self.game, clearing_number=5)
        slot5 = available_building_slot(self.clearing5)
        self.roost5 = BirdRoost.objects.filter(player=self.player, building_slot=None).first()
        self.roost5.building_slot = slot5
        self.roost5.save()


class BirdDaylightCraftingTests(BirdDaylightBaseTestCase):
    def test_disdain_for_trade_default_leader(self):
        # Despot is the default leader from factory
        leader = BirdLeader.objects.get(player=self.player, active=True)
        self.assertEqual(leader.leader, BirdLeader.BirdLeaders.DESPOT)
        
        # Give player PROTECTION_RACKET (3 VP)
        card = CardFactory(game=self.game, card_type=CardsEP.PROTECTION_RACKET.name)
        HandEntry.objects.create(player=self.player, card=card)
        
        # Craft it
        bird_craft_card(self.player, CardsEP.PROTECTION_RACKET, [self.roost3, self.roost4])
        
        # Should only score 1 VP
        self.player.refresh_from_db()
        self.assertEqual(self.player.score, 1)
        
        # Roost should be used
        self.roost3.refresh_from_db()
        self.assertTrue(self.roost3.crafted_with)
        self.roost4.refresh_from_db()
        self.assertTrue(self.roost4.crafted_with)

    def test_builder_leader_no_disdain(self):
        # Switch to Builder leader
        BirdLeader.objects.filter(player=self.player).update(active=False)
        builder = BirdLeader.objects.get(player=self.player, leader=BirdLeader.BirdLeaders.BUILDER)
        builder.active = True
        builder.save()
        
        # Give player PROTECTION_RACKET (3 VP)
        card = CardFactory(game=self.game, card_type=CardsEP.PROTECTION_RACKET.name)
        HandEntry.objects.create(player=self.player, card=card)
        
        # Craft it
        bird_craft_card(self.player, CardsEP.PROTECTION_RACKET, [self.roost3, self.roost4])
        
        # Should score full 3 VP
        self.player.refresh_from_db()
        self.assertEqual(self.player.score, 3)

    def test_rabbit_partisans_crafting(self):
        # Rabbit Partisans is not an item
        card = CardFactory(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
        HandEntry.objects.create(player=self.player, card=card)
        
        bird_craft_card(self.player, CardsEP.RABBIT_PARTISANS, [self.roost3])
        
        # Should score 0 VP
        self.player.refresh_from_db()
        self.assertEqual(self.player.score, 0)
        
        # Card should be in crafted cards
        from game.models.game_models import CraftedCardEntry
        self.assertTrue(CraftedCardEntry.objects.filter(player=self.player, card__card_type=CardsEP.RABBIT_PARTISANS.name).exists())

class BirdDecreeRecruitTests(BirdDaylightBaseTestCase):
    def setUp(self):
        super().setUp()
        self.daylight.step = BirdDaylight.BirdDaylightSteps.RECRUITING
        self.daylight.save()
        
        # Clear any existing recruit decree cards from base setup
        DecreeEntry.objects.filter(player=self.player, column=DecreeEntry.Column.RECRUIT).delete()
        
        # Add two Rabbit (Yellow) cards to recruit decree
        self.card_rabbit = CardFactory(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
        self.decree_rabbit = DecreeEntry.objects.create(player=self.player, column=DecreeEntry.Column.RECRUIT, card=self.card_rabbit)
        self.card_rabbit2 = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name) # Saboteurs is Wild/Rabbit
        self.decree_rabbit2 = DecreeEntry.objects.create(player=self.player, column=DecreeEntry.Column.RECRUIT, card=self.card_rabbit2)
        
        # Ensure enough warriors in supply
        Warrior.objects.filter(player=self.player, clearing=None).delete()
        for i in range(10):
            Warrior.objects.create(player=self.player, clearing=None)

    def test_recruit_success(self):
        # Normal leader recruits 1
        BirdLeader.objects.filter(player=self.player).update(active=False)
        despot = BirdLeader.objects.get(player=self.player, leader=BirdLeader.BirdLeaders.DESPOT)
        despot.active = True
        despot.save()
        
        bird_recruit_action(self.player, self.roost3, self.decree_rabbit)
        
        # 1 warrior placed in clearing 3
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=self.roost3.building_slot.clearing).count(), 7) # 6 initial + 1
        self.decree_rabbit.refresh_from_db()
        self.assertTrue(self.decree_rabbit.fulfilled)

    def test_charismatic_recruit_success(self):
        # Charismatic leader recruits 2
        BirdLeader.objects.filter(player=self.player).update(active=False)
        charismatic = BirdLeader.objects.get(player=self.player, leader=BirdLeader.BirdLeaders.CHARISMATIC)
        charismatic.active = True
        charismatic.save()
        
        bird_recruit_action(self.player, self.roost3, self.decree_rabbit)
        
        # 2 warriors placed in clearing 3
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=self.roost3.building_slot.clearing).count(), 8) # 6 initial + 2
        self.decree_rabbit.refresh_from_db()
        self.assertTrue(self.decree_rabbit.fulfilled)

    def test_charismatic_partial_recruit_turmoil(self):
        # Charismatic leader, only 1 warrior in supply
        BirdLeader.objects.filter(player=self.player).update(active=False)
        charismatic = BirdLeader.objects.get(player=self.player, leader=BirdLeader.BirdLeaders.CHARISMATIC)
        charismatic.active = True
        charismatic.save()
        
        Warrior.objects.filter(player=self.player, clearing=None).delete()
        Warrior.objects.create(player=self.player, clearing=None) # Only 1
        
        bird_recruit_action(self.player, self.roost3, self.decree_rabbit)
        
        # 1 warrior placed, then turmoil
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=self.roost3.building_slot.clearing).count(), 7)
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, BirdDaylight.BirdDaylightSteps.COMPLETED)
        
        # Verify turmoil event created
        from game.models.events.event import Event, EventType
        self.assertTrue(Event.objects.filter(game=self.game, type=EventType.TURMOIL).exists())

    def test_recruit_turmoil_no_supply(self):
        # No warriors in supply
        Warrior.objects.filter(player=self.player, clearing=None).delete()
        
        # Calling recruit_turmoil_check directly
        from game.transactions.birds import recruit_turmoil_check
        recruit_turmoil_check(self.player)
        
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, BirdDaylight.BirdDaylightSteps.COMPLETED)

    def test_recruit_turmoil_no_matching_roost(self):
        # No mouse clearings with roosts, but Mouse decree card
        card_mouse = CardFactory(game=self.game, card_type=CardsEP.MOUSE_PARTISANS.name)
        DecreeEntry.objects.filter(player=self.player).delete() # Clear existing
        DecreeEntry.objects.create(player=self.player, column=DecreeEntry.Column.RECRUIT, card=card_mouse)
        
        # Mouse (Orange) clearings are 2, 7, 9, 11
        # Roosts are in 3 (Rabbit) and 4 (Rabbit)
        
        from game.transactions.birds import recruit_turmoil_check
        recruit_turmoil_check(self.player)
        
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, BirdDaylight.BirdDaylightSteps.COMPLETED)

class BirdDecreeMoveTests(BirdDaylightBaseTestCase):
    def setUp(self):
        super().setUp()
        self.daylight.step = BirdDaylight.BirdDaylightSteps.MOVING
        self.daylight.save()
        
        # Clear any existing move decree cards from base setup
        DecreeEntry.objects.filter(player=self.player, column=DecreeEntry.Column.MOVE).delete()
        
        # Add two Rabbit (Yellow) cards to move decree
        self.card_rabbit = CardFactory(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
        self.decree_rabbit = DecreeEntry.objects.create(player=self.player, column=DecreeEntry.Column.MOVE, card=self.card_rabbit)
        self.card_rabbit2 = CardFactory(game=self.game, card_type=CardsEP.TUNNELS.name)
        self.decree_rabbit2 = DecreeEntry.objects.create(player=self.player, column=DecreeEntry.Column.MOVE, card=self.card_rabbit2)
        
        # Clearing 3 is Rabbit and has 6 warriors
        self.clearing3 = self.roost3.building_slot.clearing
        self.target_clearing = Clearing.objects.get(game=self.game, clearing_number=11) # Connected to 3

    def test_move_success(self):
        bird_move_action(self.player, self.clearing3, self.target_clearing, 3, self.decree_rabbit)
        
        # 3 warriors moved
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=self.clearing3).count(), 3)
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=self.target_clearing).count(), 3)
        self.decree_rabbit.refresh_from_db()
        self.assertTrue(self.decree_rabbit.fulfilled)

    def test_move_turmoil_no_warriors_in_suit(self):
        # Delete Move vizier to simplify turmoil test
        Vizier.objects.filter(player=self.player, column=Vizier.Column.MOVE).delete()
        
        # Move all warriors out of Rabbit clearings (3 and 4)
        Warrior.objects.filter(player=self.player, clearing__suit=Suit.YELLOW).update(clearing=self.target_clearing)
        
        from game.transactions.birds import move_turmoil_check
        move_turmoil_check(self.player)
        
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, BirdDaylight.BirdDaylightSteps.COMPLETED)

    def test_move_turmoil_stuck_warriors(self):
        # Delete Move vizier
        Vizier.objects.filter(player=self.player, column=Vizier.Column.MOVE).delete()
        
        # Warriors are in Rabbit clearing but can't move (no adjacency or no rule)
        # remove all connections for the clearing
        self.clearing3.connected_clearings.clear()
        
        from game.transactions.birds import move_turmoil_check
        move_turmoil_check(self.player)
        
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, BirdDaylight.BirdDaylightSteps.COMPLETED)

class BirdDecreeBattleTests(BirdDaylightBaseTestCase):
    def setUp(self):
        super().setUp()
        self.daylight.step = BirdDaylight.BirdDaylightSteps.BATTLING
        self.daylight.save()
        
        # Clear any existing battle decree cards from base setup
        DecreeEntry.objects.filter(player=self.player, column=DecreeEntry.Column.BATTLE).delete()
        
        # Add two Rabbit (Yellow) cards to battle decree
        self.card_rabbit = CardFactory(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
        self.decree_rabbit = DecreeEntry.objects.create(player=self.player, column=DecreeEntry.Column.BATTLE, card=self.card_rabbit)
        self.card_rabbit2 = CardFactory(game=self.game, card_type=CardsEP.TUNNELS.name)
        self.decree_rabbit2 = DecreeEntry.objects.create(player=self.player, column=DecreeEntry.Column.BATTLE, card=self.card_rabbit2)
        
        # Ensure Cats have a piece in clearing 3 (Rabbit)
        self.clearing3 = self.roost3.building_slot.clearing
        Warrior.objects.create(player=self.cats_player, clearing=self.clearing3)

    def test_battle_success(self):
        bird_battle_action(self.player, self.cats_player, self.clearing3, self.decree_rabbit)
        self.decree_rabbit.refresh_from_db()
        self.assertTrue(self.decree_rabbit.fulfilled)

    def test_battle_turmoil_no_enemies_in_suit(self):
        # Remove all enemy pieces (Warriors, Buildings, Tokens) from Rabbit clearings (3 and 4)
        from game.models import Building, Token
        for p in Player.objects.filter(game=self.game).exclude(pk=self.player.pk):
            Warrior.objects.filter(player=p, clearing__suit=Suit.YELLOW).delete()
            Building.objects.filter(player=p, building_slot__clearing__suit=Suit.YELLOW).delete()
            Token.objects.filter(player=p, clearing__suit=Suit.YELLOW).delete()
        
        from game.transactions.birds import battle_turmoil_check
        battle_turmoil_check(self.player)
        
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, BirdDaylight.BirdDaylightSteps.COMPLETED)

class BirdDecreeBuildTests(BirdDaylightBaseTestCase):
    def setUp(self):
        super().setUp()
        self.daylight.step = BirdDaylight.BirdDaylightSteps.BUILDING
        self.daylight.save()
        
        # Clear any existing build decree cards from base setup
        DecreeEntry.objects.filter(player=self.player, column=DecreeEntry.Column.BUILD).delete()
        
        # Add one Rabbit (Yellow) card to build decree
        self.card_rabbit = CardFactory(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
        self.decree_rabbit = DecreeEntry.objects.create(player=self.player, column=DecreeEntry.Column.BUILD, card=self.card_rabbit)


        
        # Birds need to rule a Rabbit clearing with no roost to build.
        # Clearing 10 is Rabbit. Let's make Birds rule it.
        self.clearing10 = Clearing.objects.get(game=self.game, clearing_number=10)
        # Clear any existing pieces in clearing 10
        Warrior.objects.filter(clearing=self.clearing10).delete()
        from game.models import Building, Token
        Building.objects.filter(building_slot__clearing=self.clearing10).delete()
        Token.objects.filter(clearing=self.clearing10).delete()
        # Place 1 Birds warrior to rule it
        Warrior.objects.create(player=self.player, clearing=self.clearing10)

    def test_build_success(self):
        bird_build_action(self.player, self.clearing10, self.decree_rabbit)
        # Roost placed
        from game.models.birds.buildings import BirdRoost
        self.assertTrue(BirdRoost.objects.filter(player=self.player, building_slot__clearing=self.clearing10).exists())
        self.decree_rabbit.refresh_from_db()
        self.assertTrue(self.decree_rabbit.fulfilled)

    def test_build_turmoil_no_ruled_clearings(self):
        # Remove all Birds warriors from Rabbit clearings that don't have roosts
        # Clearing 10 is the only one we set up
        Warrior.objects.filter(player=self.player, clearing=self.clearing10).delete()
        
        from game.transactions.birds import build_turmoil_check
        build_turmoil_check(self.player)
        
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, BirdDaylight.BirdDaylightSteps.COMPLETED)

    def test_build_turmoil_no_roosts_in_supply(self):
        # Place all remaining roosts on the board
        from game.models.birds.buildings import BirdRoost
        from game.models.game_models import BuildingSlot
        supply_roosts = list(BirdRoost.objects.filter(player=self.player, building_slot=None))
        for i, roost in enumerate(supply_roosts):
            slot = BuildingSlot.objects.create(clearing=self.clearing10, building_slot_number=100+i)
            roost.building_slot = slot
            roost.save()
            
        from game.transactions.birds import build_turmoil_check
        build_turmoil_check(self.player)
        
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, BirdDaylight.BirdDaylightSteps.COMPLETED)
