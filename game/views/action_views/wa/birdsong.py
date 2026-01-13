from game.models.game_models import Clearing, Faction
from game.models.wa.turn import WABirdsong
from game.queries.wa.supporters import (
    has_enough_to_revolt,
    has_enough_to_spread_sympathy,
)
from game.queries.wa.turn import validate_step
from game.serializers.general_serializers import GameActionStepSerializer
from game.transactions.wa import (
    end_revolt_step,
    end_spread_sympathy_step,
    revolt,
    spread_sympathy,
)
from game.views.action_views.general import GameActionView
from rest_framework.views import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status

from game.decorators.transaction_decorator import atomic_game_action

class RevoltView(GameActionView):
    action_name = "WA_REVOLT"
    faction = Faction.WOODLAND_ALLIANCE

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        # determine if theoretically possible to revolt
        player = self.player_by_faction(request, game_id)
        assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
        assert self.faction == Faction.WOODLAND_ALLIANCE
        if has_enough_to_revolt(player):
            self.first_step = {
                "faction": self.faction.label,
                "name": "select_clearing",
                "prompt": "Select clearing to revolt in, or choose nothing to end revolt step.",
                "endpoint": "clearing",
                "payload_details": [
                    {"type": "clearing_number", "name": "clearing_number"}
                ],
                "options": [{"value": "", "label": "Done Revolting"}],
            }
        else:
            self.first_step = {
                "faction": self.faction.label,
                "name": "end_revolt",
                "prompt": "No clearings to revolt in. confirm to end revolt step.",
                "endpoint": "end",
                "payload_details": [{"type": "confirm", "name": "confirm"}],
            }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        if route == "clearing":
            return self.post_clearing(request, game_id)
        elif route == "end":
            return self.post_end_revolt(request, game_id)
        return Response({"detail": "Invalid route"}, status=status.HTTP_404_NOT_FOUND)

    def post_clearing(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        clearing_number = request.data["clearing_number"]
        # if no clearing selected, end revolt step
        if clearing_number == "":
            try:
                atomic_game_action(end_revolt_step)(player)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        # otherwise, revolt
        clearing_number = int(clearing_number)
        try:
            clearing = clearing = Clearing.objects.get(
                game=game, clearing_number=clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        try:
            atomic_game_action(revolt)(player, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # serialize the next step
        return self.generate_completed_step()

    def post_end_revolt(self, request, game_id: int):
        confirmation = bool(request.data["confirm"])
        if confirmation:
            try:
                atomic_game_action(end_revolt_step)(self.player(request, game_id))
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        else:
            raise ValidationError("Invalid confirmation")

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        player = self.player(request, game_id)
        validate_step(player, WABirdsong.WABirdsongSteps.REVOLT)


class SpreadSympathyView(GameActionView):
    action_name = "WA_SPREAD_SYMPATHY"
    faction = Faction.WOODLAND_ALLIANCE

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        # determine if theoretically possible to spread sympathy
        player = self.player_by_faction(request, game_id)
        assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
        assert self.faction == Faction.WOODLAND_ALLIANCE
        if has_enough_to_spread_sympathy(player):
            self.first_step = {
                "faction": self.faction.label,
                "name": "select_clearing",
                "prompt": "Select clearing to spread sympathy in, or choose nothing to end spread sympathy step.",
                "endpoint": "clearing",
                "payload_details": [
                    {"type": "clearing_number", "name": "clearing_number"}
                ],
                "options": [{"value": "", "label": "Done Spreading Sympathy"}],
            }
        else:
            self.first_step = {
                "faction": self.faction.label,
                "name": "end_spread_sympathy",
                "prompt": "No clearings to spread sympathy in. confirm to end spread sympathy step.",
                "endpoint": "end",
                "payload_details": [{"type": "confirm", "name": "confirm"}],
            }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        if route == "clearing":
            return self.post_clearing(request, game_id)
        elif route == "end":
            return self.post_end_spread_sympathy(request, game_id)
        return Response({"error": "Invalid route"}, status=status.HTTP_404_NOT_FOUND)

    def post_clearing(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        clearing_number = request.data["clearing_number"]
        # if no clearing selected, end spread sympathy step
        if clearing_number == "":
            try:
                atomic_game_action(end_spread_sympathy_step)(player)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        # otherwise, spread sympathy
        clearing_number = int(clearing_number)
        try:
            clearing = clearing = Clearing.objects.get(
                game=game, clearing_number=clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        try:
            atomic_game_action(spread_sympathy)(player, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # serialize the next step
        return self.generate_completed_step()

    def post_end_spread_sympathy(self, request, game_id: int):
        confirmation = bool(request.data["confirm"])
        if confirmation:
            try:
                atomic_game_action(end_spread_sympathy_step)(self.player(request, game_id))
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        else:
            raise ValidationError("Invalid confirmation")

    def validate_timing(self, request, game_id, route, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        player = self.player(request, game_id)
        validate_step(player, WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY)
