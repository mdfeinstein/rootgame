from rest_framework.views import APIView, Response
from rest_framework.exceptions import ValidationError

from game.queries.general import player_has_warriors_in_clearing
from game.models.game_models import Clearing, Faction, Game, Player

from game.serializers.general_serializers import (
    GameActionSerializer,
    GameActionStepSerializer,
)


class GameActionView(APIView):
    action_name = None
    first_step: dict = {}
    faction: Faction | None = None

    def get(self, request, *args, **kwargs):
        """Return initial step data."""
        serializer = GameActionStepSerializer(
            self.first_step,
        )
        return Response(serializer.data)

    def post(self, request, game_id: int, route: str, *args, **kwargs):
        self.validate_player(request, game_id, route, *args, **kwargs)
        self.validate_timing(request, game_id, route, *args, **kwargs)
        return self.route_post(request, game_id, route, *args, **kwargs)

    def game(self, game_id: int):
        """Return the game. helper method. raises if game not found"""
        try:
            return Game.objects.get(pk=game_id)
        except Game.DoesNotExist:
            raise ValidationError("Game not found")

    def player(self, request, game_id: int):
        """Return the player. helper method. raises if player not found"""
        if self.faction is None:
            return self.player_by_request(request, game_id)
        else:
            return self.player_by_faction(request, game_id)

    def player_by_request(self, request, game_id: int):
        """Return the player according to the request token. helper method. raises if player not found"""
        try:
            return Player.objects.get(game=game_id, user=request.user)
        except Player.DoesNotExist:
            raise ValidationError("Player not found")

    def player_by_faction(self, request, game_id: int):
        """Return the player according to the faction. helper method. raises if player not found"""
        try:
            return Player.objects.get(game=game_id, faction=self.faction)
        except Player.DoesNotExist:
            raise ValidationError("Player not found")

    def validate_player(self, request, game_id: int, route: str, *args, **kwargs):
        """validate that player making a post request is the correct faction"""
        player_requesting = self.player_by_request(request, game_id)

        if self.faction is not None:
            player_of_faction_in_game = self.player_by_faction(request, game_id)
            if player_requesting != player_of_faction_in_game:
                raise ValidationError(
                    "Player is not the correct faction for this action"
                )
        else:
            pass

    def validate_timing(self, request, game_id: int, route: str, *args, **kwargs):
        """raises if not this player's turn or correct step. called in post.
        should be implemented by any subclass with timing dependency"""
        pass

    def route_post(
        self, request, game_id: int, route: str, *args, **kwargs
    ) -> Response:
        """called in post. should be implemented by any subclass
        player and timing validation, if defined, will be called in post.
        """
        raise ValidationError("No routes defined")

    def generate_step(
        self,
        name,
        prompt,
        endpoint,
        payload_details,
        accumulated_payload: dict | None = None,
        faction: Faction | None = None,
    ):
        if faction is None:
            faction = self.faction.label
        step = {
            "faction": self.faction.label if self.faction is not None else "",
            "name": name,
            "prompt": prompt,
            "endpoint": endpoint,
            "payload_details": payload_details,
            "accumulated_payload": accumulated_payload,
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def generate_completed_step(self):
        step = {"name": "completed"}
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)


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
