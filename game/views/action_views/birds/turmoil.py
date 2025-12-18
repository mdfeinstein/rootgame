from rest_framework.exceptions import ValidationError
from rest_framework.views import Response
from rest_framework import status

from game.models.birds.player import BirdLeader
from game.models.game_models import Faction
from game.queries.birds.leaders import get_available_leaders
from game.queries.birds.turn import get_turmoil_event
from game.transactions.birds import turmoil_choose_new_leader
from game.views.action_views.general import GameActionView


class TurmoilView(GameActionView):
    name = "turmoil"
    faction = Faction.BIRDS

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        player = self.player(request, game_id)
        available_leaders = get_available_leaders(player)
        leader_labels = [leader.leader.label for leader in available_leaders]
        self.first_step = {
            "faction": self.faction.label,
            "name": "new_leader",
            "prompt": "Choose a new leader to resolve the turmoil event. Available leaders: "
            + ", ".join(leader_labels),
            "endpoint": "new_leader",
            "payload_details": [
                {"type": "leader", "name": "new_leader"},
            ],
        }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "new_leader":
                return self.post_new_leader(request, game_id)
            case _:
                return Response(
                    {"detail": "Invalid route"}, status=status.HTTP_404_NOT_FOUND
                )

    def post_new_leader(self, request, game_id: int):
        new_leader = request.data["new_leader"].upper()
        try:
            leader = BirdLeader.BirdLeaders[new_leader]
        except KeyError:
            raise ValidationError("Invalid leader")
        game = self.game(game_id)
        player = self.player(request, game_id)
        leader = BirdLeader.objects.get(player=player, leader=leader)
        try:
            turmoil_choose_new_leader(player, leader)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not the correct step"""
        game = self.game(game_id)
        player = self.player(request, game_id)
        try:
            get_turmoil_event(player)
        except ValueError:
            raise ValidationError("Not the correct step")
