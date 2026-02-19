from django.urls import reverse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

from game.models.birds.setup import BirdsSimpleSetup
from game.models.cats.setup import CatsSimpleSetup
from game.models.cats.turn import CatBirdsong, CatDaylight, CatTurn
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import (
    Clearing,
    DiscardPileEntry,
    Faction,
    Game,
    HandEntry,
    Player,
)
from game.queries.cats.turn import get_phase as get_cat_phase
from game.queries.current_action.setup import get_setup_action
from game.queries.current_action.turns import get_current_turn_action
from game.serializers.general_serializers import (
    CardSerializer,
    GameStatusSerializer,
    PlayerPublicSerializer,
    GameSessionSerializer,
    ClearingSerializer,
)
from game.logic.playback import undo_last_action
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@api_view(["GET"])
def get_discard_pile(request, game_id: int):
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response(
            {"message": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
        )
    # add auth: valid player or spectator
    discarded_cards = DiscardPileEntry.objects.filter(game=game)
    serializer = CardSerializer([card.card for card in discarded_cards], many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_player_hand(request, game_id: int):
    # TODO: add auth: valid player or spectator
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return ValidationError("Game does not exist")
    try:
        player = Player.objects.get(user=request.user, game=game)
    except Player.DoesNotExist:
        return ValidationError("Player does not exist")
    hand_cards = HandEntry.objects.filter(player=player)
    serializer = CardSerializer([card.card for card in hand_cards], many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_clearings(request, game_id: int):
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response(
            {"message": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
        )
    clearings = Clearing.objects.filter(game=game)
    serializer = ClearingSerializer(clearings, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_turn_info(request, game_id: int):
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        raise ValidationError("Game does not exist")
    serializer = GameStatusSerializer.from_game(game)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_current_action(request, game_id: int):
    """provides the route for the current action"""
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        raise ValidationError("Game does not exist")
    setup_action = get_setup_action(game)
    if setup_action is not None:
        return Response({"route": setup_action})
    # else, move on to turns
    turn_action = get_current_turn_action(game)
    if turn_action is not None:
        return Response({"route": turn_action})
    # else, move on to...
    raise ValidationError("Not yet implemented")


@api_view(["GET"])
def get_players(request, game_id: int):
    """provides information about all players in the game"""
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        raise ValidationError("Game does not exist")
    players = Player.objects.filter(game=game)
    serializer = PlayerPublicSerializer(players, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
def undo_last_action_view(request, game_id: int):
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response({"detail": "Game not found"}, status=status.HTTP_404_NOT_FOUND)

    undo_last_action(game)

    # Publish update to WebSocket
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"game_{game.id}", {"type": "game_update", "message": "update"}
        )
    except Exception as e:
        print(f"Failed to send websocket update: {e}")

    return Response({"status": "success"}, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_game_session_detail(request, game_id: int):
    """provides detailed information about the game session"""
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response({"detail": "Game not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = GameSessionSerializer(game)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_dominance_supply(request, game_id: int):
    """
    Returns the dominance cards currently available in the supply.
    """
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response({"detail": "Game not found"}, status=status.HTTP_404_NOT_FOUND)

    from game.models.dominance import DominanceSupplyEntry
    from game.serializers.general_serializers import DominanceSupplyEntrySerializer

    supply_entries = DominanceSupplyEntry.objects.filter(game=game)
    serializer = DominanceSupplyEntrySerializer(supply_entries, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)
