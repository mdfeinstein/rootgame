from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from game.models.game_models import Player
from game.serializers.general_serializers import PlayerSerializer, UserSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_player_info(request, game_id):
    user = request.user
    player = Player.objects.get(game=game_id, user=user)
    serializer = PlayerSerializer(player)
    return Response(serializer.data)
