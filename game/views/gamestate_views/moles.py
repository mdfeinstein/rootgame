from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from drf_spectacular.utils import extend_schema

from game.models.game_models import Faction, Game, Player
from game.serializers.moles_serializers import MolesSerializer


@extend_schema(responses={200: MolesSerializer})
@api_view(["GET"])
def get_moles_player_public(request, game_id: int):
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response(
            {"message": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
        )
    try:
        moles_player = Player.objects.get(game=game, faction=Faction.MOLES)
    except Player.DoesNotExist:
        return Response(
            {"message": "Moles player does not exist in this game"},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = MolesSerializer.from_player(moles_player)
    return Response(serializer.data, status=status.HTTP_200_OK)
