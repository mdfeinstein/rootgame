from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from game.models.game_models import Faction, Game, Player
from game.serializers.cat_serializers import CatSerializer


@api_view(["GET"])
def get_cat_player_public(request, game_id: int):
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response(
            {"message": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
        )
    # add auth: valid player or spectator
    try:
        cat_player = Player.objects.get(game=game, faction=Faction.CATS)
    except Player.DoesNotExist:
        return Response(
            {"message": "Cat player does not exist in this game"},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = CatSerializer.from_player(cat_player)
    return Response(serializer.data, status=status.HTTP_200_OK)
