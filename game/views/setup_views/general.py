from typing import Any, cast

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import api_view
from rest_framework import serializers
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    APIException,
    ValidationError,
)
from django.contrib.auth.models import User

from game.models.game_models import Faction, FactionChoiceEntry, Game, Player
from game.serializers.general_serializers import (
    CreateNewGameSerializer,
    FactionChoiceSerializer,
    GameListSerializer,
)
from game.transactions.game_setup import (
    add_new_player_to_game,
    assign_turn_order,
    autumn_map_setup,
    begin_faction_setup,
    construct_deck,
    create_craftable_item_supply,
    create_new_game,
    map_setup,
    player_picks_faction,
    start_game,
)


@api_view(["POST"])
def create_game(request: Request):
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to create a game")
    user = cast(User, request.user)
    serializer = CreateNewGameSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    assert isinstance(serializer.validated_data, dict)
    data: dict[str, Any] = serializer.validated_data
    # get board choice or default to autumn
    map = data.get("map_label", Game.BoardMaps.AUTUMN)

    # get faction choices, defaulting to full list
    faction_options = data.get(
        "faction_options", [faction.value for faction in Faction]
    )
    game = create_new_game(owner=user, map=map, faction_options=faction_options)
    return Response({"game_id": game.pk}, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
def join_game(request: Request, game_id: int):
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to join a game")
    user = cast(User, request.user)
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        raise NotFound("Game does not exist")
    try:
        add_new_player_to_game(game, user)
    except ValueError as e:
        raise ValidationError({"detail": str(e)})
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
def pick_faction(request: Request, game_id: int):
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to pick a faction")
    user = cast(User, request.user)
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        raise NotFound("Game does not exist")
    try:
        player = Player.objects.get(game=game, user=user)
    except Player.DoesNotExist:
        raise NotFound("Player does not exist")
    serializer = FactionChoiceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    assert isinstance(serializer.validated_data, dict)
    data: dict[str, Any] = serializer.validated_data
    # look up faction choice
    faction = data.get("faction")  # serializer has raised if not found
    try:
        faction_entry = FactionChoiceEntry.objects.get(game=game, faction=faction)
    except FactionChoiceEntry.DoesNotExist:
        raise NotFound("Faction choice does not exist")
    try:
        player_picks_faction(player, faction_entry)
    except ValueError as e:
        raise ValidationError({"detail": str(e)})
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
def start_game_view(request: Request, game_id: int):
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to start a game")
    user = cast(User, request.user)
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        raise NotFound("Game does not exist")
    if game.owner != user:
        raise PermissionDenied("User is not the owner of the game")

    # game set up stuff
    # random assignment of turn order (for now)
    assign_turn_order(game)
    try:
        start_game(game)
    except ValueError as e:
        raise ValidationError({"detail": str(e)})
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def get_player_turn(request: Request, game_id: int):
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to get turn")


@api_view(["GET"])
def list_active_games(request: Request):
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to list games")
    user = cast(User, request.user)
    # games where the user is a player
    games = Game.objects.filter(players__user=user).distinct().order_by("-id")
    serializer = GameListSerializer(games, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
def list_joinable_games(request: Request):
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to list games")
    user = cast(User, request.user)
    # games that haven't started and user is not a player
    games = (
        Game.objects.filter(status=Game.GameStatus.NOT_STARTED)
        .exclude(players__user=user)
        .order_by("-id")
    )
    serializer = GameListSerializer(games, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["POST"])
def create_demo_game(request: Request):
    """
    Creates a new demo game, adds user1, user2, user3. 
    Assigns them Cats, Birds, and WA respectively, and starts the game.
    """
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to create a demo game")
    
    # 1. Create the game
    map_label = Game.BoardMaps.AUTUMN
    faction_options = [faction.value for faction in Faction]
    game = create_new_game(owner=request.user, map=map_label, faction_options=faction_options)

    # 2. Find the users
    try:
        user1 = User.objects.get(username="user1")
        user2 = User.objects.get(username="user2")
        user3 = User.objects.get(username="user3")
    except User.DoesNotExist:
        # If the users don't exist for some reason, hard fail.
        raise ValidationError({"detail": "Demo users (user1, user2, user3) not found in the system."})

    # 3. Add users to the game
    # The owner (request.user) might be one of user1, user2, or user3. 
    # create_new_game already adds the owner as a player. 
    # We should ensure we don't add them twice or crash.
    for u in [user1, user2, user3]:
        # Only add if they aren't already a player
        if not Player.objects.filter(game=game, user=u).exists():
            add_new_player_to_game(game, u)

    # 4. Pick factions
    # user1 -> Cats, user2 -> Birds, user3 -> WA
    faction_map = {
        user1: Faction.CATS,
        user2: Faction.BIRDS,
        user3: Faction.WOODLAND_ALLIANCE
    }
    
    for u, faction_val in faction_map.items():
        player = Player.objects.get(game=game, user=u)
        faction_entry = FactionChoiceEntry.objects.get(game=game, faction=faction_val)
        player_picks_faction(player, faction_entry)

    # 5. Start the game
    assign_turn_order(game)
    try:
        start_game(game)
    except ValueError as e:
        raise ValidationError({"detail": str(e)})

    return Response({"game_id": game.pk}, status=status.HTTP_201_CREATED)
