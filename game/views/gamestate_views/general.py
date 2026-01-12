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
from game.queries.general import get_current_player
from game.serializers.general_serializers import (
    CardSerializer,
    ClearingSerializer,
    GameStatusSerializer,
    PlayerPublicSerializer,
)


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
def get_player_hand(request):
    # TODO: add auth: valid player or spectator
    try:
        player = Player.objects.get(user=request.user)
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
