from rest_framework.views import APIView, Response
from rest_framework.exceptions import ValidationError

from game.db_selectors.general import player_has_warriors_in_clearing
from game.models.game_models import Clearing, Faction, Game, Player

from game.serializers.general_serializers import (
    GameActionSerializer,
    GameActionStepSerializer,
)


class GameActionView(APIView):
    action_name = None
    first_step: dict = {}
    # faction: Faction = None

    def get(self, request, *args, **kwargs):
        """Return initial step data."""
        serializer = GameActionStepSerializer(
            self.first_step,
        )
        return Response(serializer.data)

    def game(self, game_id: int):
        """Return the game. helper method. raises if game not found"""
        try:
            return Game.objects.get(pk=game_id)
        except Game.DoesNotExist:
            raise ValidationError("Game not found")

    def player(self, request, game_id: int):
        """Return the player. helper method. raises if player not found"""
        try:
            return Player.objects.get(game=game_id, user=request.user)
        except Player.DoesNotExist:
            raise ValidationError("Player not found")


class MovePiecesView(GameActionView):
    action_name = "MOVE_PIECES"

    steps = [
        {
            "prompt": "Select source clearing",
            "endpoint": "source",
            "payload_type": "clearing",
        },
        {
            "prompt": "Select destination",
            "endpoint": "destination",
            "payload_type": "clearing",
        },
        {"prompt": "Choose number", "endpoint": "count", "payload_type": "number"},
        {"prompt": "Confirm move", "endpoint": "confirm", "payload_type": "confirm"},
    ]

    def post_source(self, request, game_id: int):
        game = self.game(request)
        player = Player.objects.get(game=game, user=request.user)
        clearing_number = request.data["clearing_number"]
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        if not player_has_warriors_in_clearing(player, clearing):
            raise ValidationError("You do not have warriors in that clearing")
        return Response({"clearing": clearing})

    def post_destination(self, request, *args, **kwargs): ...

    def post_count(self, request, *args, **kwargs): ...
    def post_confirm(self, request, *args, **kwargs): ...
