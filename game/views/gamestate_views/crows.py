from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from game.models.game_models import Faction, Game, Player
from game.models.crows.exposure import ExposureRevealedCards
from game.serializers.crows_serializers import CrowsSerializer, CrowsPrivateSerializer


@api_view(["GET"])
def get_crows_player_public(request, game_id: int):
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response(
            {"message": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
        )

    try:
        crows_player = Player.objects.get(game=game, faction=Faction.CROWS)
    except Player.DoesNotExist:
        return Response(
            {"message": "Crows player does not exist in this game"},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = CrowsSerializer.from_player(crows_player)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_crows_player_private(request, game_id: int):
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response(
            {"message": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
        )

    try:
        crows_player = Player.objects.get(game=game, user=request.user)
    except Player.DoesNotExist:
        return Response(
            {"message": "Player does not exist in this game"},
            status=status.HTTP_404_NOT_FOUND,
        )
        
    if crows_player.faction != Faction.CROWS:
        return Response(
            {"message": "Requesting player is not the Crows player"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
        
    revealed_card_entries = ExposureRevealedCards.objects.filter(player=crows_player)
    cards = [entry.card for entry in revealed_card_entries]
    
    # We populate tokens explicitly unmasked via the dict below
    
    # Since we need to combine from_player tokens with the cards query,
    # let's map it into the context or directly add it.
    # We can serialize the base instance from_player, and then manually attach the serialized cards,
    # OR better, pass it into the from_player method. Let's update `from_player` to take cards if needed,
    # But CrowsPrivateSerializer doesn't have a from_player taking cards right now. Let's just modify the dict data before Response.
    
    # Let's fix this cleanly. CrowsPrivateSerializer already has `exposure_revealed_cards = CardSerializer(many=True)`
    # Thus we can just instantiate it with the keys it expects:
    from game.models.crows.tokens import PlotToken
    
    reserve = PlotToken.objects.filter(player=crows_player, clearing__isnull=True)
    board = PlotToken.objects.filter(player=crows_player, clearing__isnull=False)
    
    instance = {
        "reserve_plots": reserve,
        "facedown_plots": board.filter(is_facedown=True),
        "exposure_revealed_cards": cards
    }
    
    serializer = CrowsPrivateSerializer(instance=instance)
    return Response(serializer.data, status=status.HTTP_200_OK)
