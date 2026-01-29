from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.models.game_models import Game, Player, Faction, CraftedCardEntry
from game.serializers.general_serializers import CraftedCardSerializer

class GetCraftedCardsView(APIView):
    def get(self, request, game_id, faction):
        game = get_object_or_404(Game, pk=game_id)
        try:
            #assume slug is bi, wa, ca
            faction_value = Faction(faction).value
        except ValueError:
            return Response({"error": "Invalid faction"}, status=status.HTTP_400_BAD_REQUEST)
        player = get_object_or_404(Player, game=game, faction=faction_value)
        
        # Get crafted cards
        crafted_cards = CraftedCardEntry.objects.filter(player=player).select_related('card')
        
        serializer = CraftedCardSerializer(crafted_cards, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
