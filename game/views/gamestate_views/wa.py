from game.models.wa.player import SupporterStackEntry
from game.serializers.wa_serializers import WAPrivateSerializer
from game.serializers.general_serializers import CardSerializer
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from game.models.game_models import Faction, Game, Player
from game.serializers.wa_serializers import WASerializer


@api_view(["GET"])
def get_wa_player_public(request, game_id: int):
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response(
            {"message": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
        )

    try:
        wa_player = Player.objects.get(game=game, faction=Faction.WOODLAND_ALLIANCE)
    except Player.DoesNotExist:
        return Response(
            {"message": "WA player does not exist in this game"},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = WASerializer.from_player(wa_player)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["GET"])
def get_wa_player_private(request, game_id: int):
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response(
            {"message": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
        )

    try:
        wa_player = Player.objects.get(game=game, user = request.user)
    except Player.DoesNotExist:
        return Response(
            {"message": "player does not exist in this game"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if wa_player.faction != Faction.WOODLAND_ALLIANCE:
        return Response(
            {"message": "requesting player is not the WA player"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    supporter_cards = SupporterStackEntry.objects.filter(player=wa_player)
    cards = [supporter_card.card for supporter_card in supporter_cards]
    serializer = WAPrivateSerializer({"supporter_cards": cards})
    return Response(serializer.data, status=status.HTTP_200_OK)
