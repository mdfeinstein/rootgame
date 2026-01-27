import factory
from django.contrib.auth.models import User
from game.models.game_models import (
    Game, Player, Faction, Card, HandEntry, CraftedCardEntry, 
    Warrior, Clearing, Suit, FactionChoiceEntry, Item, CraftedItemEntry,
    DiscardPileEntry
)
from game.game_data.general.game_enums import ItemTypes
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.turn import BirdTurn
from game.models.cats.turn import CatTurn
from game.models.wa.turn import WATurn

from game.transactions.game_setup import (
    create_new_game, 
    add_new_player_to_game, 
    player_picks_faction, 
    start_game as tx_start_game
)

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@example.com")


class GameFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Game

    owner = factory.SubFactory(UserFactory)
    boardmap = Game.BoardMaps.AUTUMN
    status = Game.GameStatus.NOT_STARTED


class PlayerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Player

    user = factory.SubFactory(UserFactory)
    game = factory.SubFactory(GameFactory)
    faction = Faction.BIRDS
    turn_order = 0


class CardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Card

    game = factory.SubFactory(GameFactory)
    card_type = CardsEP.FOXFOLK_STEEL.name


class DiscardPileEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DiscardPileEntry

    game = factory.SubFactory(GameFactory)
    card = factory.SubFactory(CardFactory, game=factory.SelfAttribute('..game'))
    spot = factory.Sequence(lambda n: n)

class HandEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HandEntry

    player = factory.SubFactory(PlayerFactory)
    card = factory.SubFactory(CardFactory, game=factory.SelfAttribute('..player.game'))


class CraftedCardEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CraftedCardEntry

    player = factory.SubFactory(PlayerFactory)
    card = factory.SubFactory(CardFactory, game=factory.SelfAttribute('..player.game'))
    used = CraftedCardEntry.UsedChoice.UNUSED


class ClearingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Clearing

    game = factory.SubFactory(GameFactory)
    clearing_number = factory.Sequence(lambda n: n % 12 + 1)
    suit = Suit.RED


class WarriorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Warrior

    player = factory.SubFactory(PlayerFactory)
    clearing = None


class ItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Item

    game = factory.SubFactory(GameFactory)
    item_type = ItemTypes.BOOTS.value
    exhausted = False


class CraftedItemEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CraftedItemEntry

    player = factory.SubFactory(PlayerFactory)
    item = factory.SubFactory(ItemFactory, game=factory.SelfAttribute('..player.game'))
    exhausted = False


class BirdTurnFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BirdTurn
    
    player = factory.SubFactory(PlayerFactory, faction=Faction.BIRDS)
    turn_number = 1

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        player = kwargs.get('player')
        return model_class.create_turn(player=player)


class CatTurnFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CatTurn

    player = factory.SubFactory(PlayerFactory, faction=Faction.CATS)
    turn_number = 1

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        player = kwargs.get('player')
        return model_class.create_turn(player=player)


class WATurnFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WATurn

    player = factory.SubFactory(PlayerFactory, faction=Faction.WOODLAND_ALLIANCE)
    turn_number = 1

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        player = kwargs.get('player')
        return model_class.create_turn(player=player)


class GameSetupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Game

    owner = factory.SubFactory(UserFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        owner = kwargs.get('owner')
        if not owner:
            owner = UserFactory()
            
        boardmap = kwargs.get('boardmap', Game.BoardMaps.AUTUMN)
        factions = kwargs.get('factions', [Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE]) 
        
        game = create_new_game(owner, boardmap, factions)
        
        users = kwargs.get('users', [])
        if not users:
            users = [owner]
            while len(users) < len(factions):
                 users.append(UserFactory())
        
        created_players = []
        for i, user in enumerate(users):
            if i >= len(factions): 
                break
                
            player = add_new_player_to_game(game, user)
            created_players.append(player)
            
            faction_to_pick = factions[i]
            choice_entry = FactionChoiceEntry.objects.get(game=game, faction=faction_to_pick)
            player_picks_faction(player, choice_entry)
            
            player.turn_order = i
            player.save()
            
        tx_start_game(game)
        
        return game

class GameSetupWithFactionsFactory(GameSetupFactory):
    class Meta:
        model = Game

    # PostGeneration hook to run faction setup steps
    @factory.post_generation
    def complete_setup(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing
            return

        # 1. Cats Setup
        cats_player = Player.objects.filter(game=self, faction=Faction.CATS).first()
        if cats_player:
            from game.transactions.cats_setup import pick_corner, place_initial_building, confirm_completed_setup
            cats_pick_corner = pick_corner
            cats_place_initial_building = place_initial_building
            cats_finish_setup = confirm_completed_setup
            cats_pick_corner(cats_player, Clearing.objects.get(game=self, clearing_number=1))
            # Place Sawmill in 1, Workshop in 5, Recruiter in 9 (connected clearings in Autumn map)
            from game.models.cats.buildings import CatBuildingTypes
            cats_place_initial_building(cats_player, Clearing.objects.get(game=self, clearing_number=1), CatBuildingTypes.SAWMILL)
            cats_place_initial_building(cats_player, Clearing.objects.get(game=self, clearing_number=5), CatBuildingTypes.WORKSHOP)
            cats_place_initial_building(cats_player, Clearing.objects.get(game=self, clearing_number=9), CatBuildingTypes.RECRUITER)
            cats_finish_setup(cats_player)
            
        # 2. Birds Setup
        birds_player = Player.objects.filter(game=self, faction=Faction.BIRDS).first()
        if birds_player:
            from game.transactions.birds_setup import pick_corner, choose_leader_initial, confirm_completed_setup
            from game.models.birds.player import BirdLeader
            birds_pick_corner = pick_corner
            birds_pick_leader = choose_leader_initial
            birds_finish_setup = confirm_completed_setup
            # Pick opposite corner (3). Corners are 1,2,3,4. Opposite of 1 is 3.
            birds_pick_corner(birds_player, Clearing.objects.get(game=self, clearing_number=3))
            birds_pick_leader(birds_player, BirdLeader.BirdLeaders.DESPOT)
            birds_finish_setup(birds_player)
            
        # 3. WA Setup
        wa_player = Player.objects.filter(game=self, faction=Faction.WOODLAND_ALLIANCE).first()
        if wa_player:
            # WA setup is mostly automatic (drawing cards), usually handled by initial setup.
            # But let's check if there's any manual step.
            pass
            
        # No need to manually create the first turn here anymore.
        # The faction setup transactions (confirm_completed_setup) or start_game 
        # now handle this as part of the formal game initialization flow.

