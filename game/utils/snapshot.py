from django.core import serializers
from itertools import chain

# Import all models
from game.models.game_models import (
    Game,
    FactionChoiceEntry,
    Clearing,
    BuildingSlot,
    Warrior,
    Building,
    Token,
    Ruin,
    Piece,
    Card,
    DeckEntry,
    DiscardPileEntry,
    Item,
    CraftableItemEntry,
    CraftedItemEntry,
    CraftedCardEntry,
    HandEntry,
    WarriorSupplyEntry,
)
from game.models.dominance import DominanceSupplyEntry, ActiveDominanceEntry
from game.models.birds.player import BirdLeader, DecreeEntry, Vizier
from game.models.birds.buildings import BirdRoost
from game.models.birds.turn import BirdTurn, BirdBirdsong, BirdDaylight, BirdEvening

from game.models.cats.buildings import Workshop, Sawmill, Recruiter
from game.models.cats.tokens import CatKeep, CatWood
from game.models.cats.turn import CatTurn, CatBirdsong, CatDaylight, CatEvening

from game.models.wa.buildings import WABase
from game.models.wa.tokens import WASympathy
from game.models.wa.player import SupporterStackEntry, OfficerEntry
from game.models.wa.turn import WATurn, WABirdsong, WADaylight, WAEvening

from game.models.events.event import Event
from game.models.events.battle import Battle
from game.models.events.wa import OutrageEvent
from game.models.events.birds import TurmoilEvent
from game.models.events.cats import FieldHospitalEvent
from game.models.events.setup import GameSimpleSetup
from game.models.cats.setup import CatsSimpleSetup
from game.models.birds.setup import BirdsSimpleSetup
from game.models.events.crafted_cards import (
    InformantsEvent,
    EyrieEmigreEvent,
    SaboteursEvent,
    CharmOffensiveEvent,
    PartisansEvent,
    SwapMeetEvent,
)


def get_all_game_objects(game: Game):
    """
    Collects all model instances related to the given game instance.
    Returns a list of objects in an order suitable for serialization (dependencies first).
    """
    objects = []

    # 1. Root Game Object
    objects.append(game)

    # 2. Static-ish components (depend on Game)
    objects.extend(FactionChoiceEntry.objects.filter(game=game))
    objects.extend(Clearing.objects.filter(game=game))
    # BuildingSlot depends on Clearing
    objects.extend(BuildingSlot.objects.filter(clearing__game=game))

    # Cards & Items (Global/Game level)
    objects.extend(Card.objects.filter(game=game))
    objects.extend(Item.objects.filter(game=game))

    # Game State Collections (Deck, Discard, Ruins, Craftable)
    objects.extend(DeckEntry.objects.filter(game=game))
    objects.extend(DiscardPileEntry.objects.filter(game=game))
    objects.extend(Ruin.objects.filter(game=game))
    objects.extend(CraftableItemEntry.objects.filter(game=game))
    objects.extend(DominanceSupplyEntry.objects.filter(game=game))

    # Setup State (depend on Game)
    objects.extend(GameSimpleSetup.objects.filter(game=game))

    # 3. Players and their direct assets
    players = game.players.all().order_by("turn_order")
    objects.extend(players)

    for player in players:
        # Player generic assets
        objects.extend(HandEntry.objects.filter(player=player))
        objects.extend(CraftedItemEntry.objects.filter(player=player))
        objects.extend(CraftedCardEntry.objects.filter(player=player))
        objects.extend(ActiveDominanceEntry.objects.filter(player=player))
        objects.extend(WarriorSupplyEntry.objects.filter(player=player))

        # Setup state (depend on Player)
        objects.extend(CatsSimpleSetup.objects.filter(player=player))
        objects.extend(BirdsSimpleSetup.objects.filter(player=player))

        # Pieces (Warriors, Buildings, Tokens)
        # For MTI (Multi-Table Inheritance), we MUST serialize the base models as well
        # to capture the inherited fields (like 'player' on Piece, 'clearing' on Token).
        # Order matters: Base -> Child.

        # 3a. Base Piece (Parent of Token, Building, Warrior)
        # Note: We filter by player to keep it organized, though we could do bulk query.
        objects.extend(Piece.objects.filter(player=player))

        # 3b. Intermediate Bases (Token, Building)
        objects.extend(Token.objects.filter(player=player))
        objects.extend(Building.objects.filter(player=player))

        # 3c. Leaf Classes
        # Warriors (Direct child of Piece)
        objects.extend(Warrior.objects.filter(player=player))

        # Faction Specific Assets & Pieces
        # Birds
        objects.extend(BirdLeader.objects.filter(player=player))
        objects.extend(DecreeEntry.objects.filter(player=player))
        objects.extend(Vizier.objects.filter(player=player))
        objects.extend(BirdRoost.objects.filter(player=player))

        # Cats
        objects.extend(Workshop.objects.filter(player=player))
        objects.extend(Sawmill.objects.filter(player=player))
        objects.extend(Recruiter.objects.filter(player=player))
        objects.extend(CatKeep.objects.filter(player=player))
        objects.extend(CatWood.objects.filter(player=player))

        # WA
        objects.extend(WABase.objects.filter(player=player))
        objects.extend(WASympathy.objects.filter(player=player))
        objects.extend(SupporterStackEntry.objects.filter(player=player))
        objects.extend(OfficerEntry.objects.filter(player=player))

        # Turn History / State
        # Birds
        bird_turns = BirdTurn.objects.filter(player=player)
        objects.extend(bird_turns)
        objects.extend(BirdBirdsong.objects.filter(turn__in=bird_turns))
        objects.extend(BirdDaylight.objects.filter(turn__in=bird_turns))
        objects.extend(BirdEvening.objects.filter(turn__in=bird_turns))

        # Cats
        cat_turns = CatTurn.objects.filter(player=player)
        objects.extend(cat_turns)
        objects.extend(CatBirdsong.objects.filter(turn__in=cat_turns))
        objects.extend(CatDaylight.objects.filter(turn__in=cat_turns))
        objects.extend(CatEvening.objects.filter(turn__in=cat_turns))

        # WA
        wa_turns = WATurn.objects.filter(player=player)
        objects.extend(wa_turns)
        objects.extend(WABirdsong.objects.filter(turn__in=wa_turns))
        objects.extend(WADaylight.objects.filter(turn__in=wa_turns))
        objects.extend(WAEvening.objects.filter(turn__in=wa_turns))

    # 4. Events
    # Events depend on Game, but sub-events depend on Event + Players/Clearings
    events = Event.objects.filter(game=game)
    objects.extend(events)
    # Sub-events (OneToOne)
    objects.extend(Battle.objects.filter(event__in=events))
    objects.extend(OutrageEvent.objects.filter(event__in=events))
    objects.extend(TurmoilEvent.objects.filter(event__in=events))
    objects.extend(FieldHospitalEvent.objects.filter(event__in=events))
    objects.extend(InformantsEvent.objects.filter(event__in=events))
    objects.extend(EyrieEmigreEvent.objects.filter(event__in=events))
    objects.extend(SaboteursEvent.objects.filter(event__in=events))
    objects.extend(CharmOffensiveEvent.objects.filter(event__in=events))
    objects.extend(PartisansEvent.objects.filter(event__in=events))
    objects.extend(SwapMeetEvent.objects.filter(event__in=events))

    return objects


import json


def capture_gamestate(game: Game) -> list:
    """
    Captures the full state of the game as a list of dicts (fixture format).
    Ensures datetimes are serialized to strings for JSONField compatibility.
    """
    objects = get_all_game_objects(game)
    # Use 'json' serializer to handle datetimes, then load back to a list of dicts
    json_data = serializers.serialize("json", objects)
    return json.loads(json_data)
