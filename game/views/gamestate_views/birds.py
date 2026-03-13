from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from drf_spectacular.utils import extend_schema

from game.models.game_models import Faction, Game, Player
from game.serializers.bird_serializers import BirdSerializer


@extend_schema(responses={200: BirdSerializer})
@api_view(["GET"])
def get_bird_player_public(request, game_id: int):
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response(
            {"message": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
        )
    # add auth: valid player or spectator
    try:
        bird_player = Player.objects.get(game=game, faction=Faction.BIRDS)
    except Player.DoesNotExist:
        return Response(
            {"message": "Bird player does not exist in this game"},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = BirdSerializer.from_player(bird_player)
    return Response(serializer.data, status=status.HTTP_200_OK)
