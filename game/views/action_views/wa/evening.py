from game.models.game_models import Clearing, Faction, Player
from game.models.wa.turn import WAEvening
from game.queries.general import (
    player_has_warriors_in_clearing,
    validate_enemy_pieces_in_clearing,
    validate_has_legal_moves,
    validate_legal_move,
)
from game.queries.wa.actions import get_unused_officer_count
from game.queries.wa.turn import validate_step
from game.transactions.wa import (
    end_evening_operations,
    operation_battle,
    operation_move,
    operation_organize,
    operation_recruit,
)
from game.views.action_views.general import GameActionView
from rest_framework.views import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError


class WAOperationsView(GameActionView):
    action_name = "WA_EVENING"
    faction = Faction.WOODLAND_ALLIANCE
    first_step = {
        "faction": faction.label,
        "name": "select_operation",
        "prompt": "Select operation: recruit, move, battle, or organize. Or, choose nothing to end operation step.",
        "endpoint": "operation",
        "payload_details": [{"type": "action_type", "name": "operation"}],
    }

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        operations_remaining = get_unused_officer_count(
            self.player_by_faction(request, game_id)
        )
        assert self.faction == Faction.WOODLAND_ALLIANCE
        if operations_remaining == 0:
            self.first_step = {
                "faction": self.faction.label,
                "name": "end_operations",
                "prompt": "No operations remaining. confirm to end operation step.",
                "endpoint": "end",
                "payload_details": [{"type": "confirm", "name": "confirm"}],
            }

        self.first_step = {
            "faction": self.faction.label,
            "name": "select_operation",
            "prompt": "Select operation: recruit, move, battle, or organize. Or, choose nothing to end operation step."
            + f"Operations remaining: {operations_remaining}",
            "endpoint": "operation",
            "payload_details": [{"type": "action_type", "name": "operation"}],
        }

        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "operation":
                return self.post_operation(request, game_id)
            case "recruit":
                return self.post_recruit(request, game_id)
            case "move-origin":
                return self.post_move_origin(request, game_id)
            case "move-destination":
                return self.post_move_destination(request, game_id)
            case "move-count":
                return self.post_move_count(request, game_id)
            case "battle-clearing":
                return self.post_battle_clearing(request, game_id)
            case "battle-defender":
                return self.post_battle_defender(request, game_id)
            case "organize":
                return self.post_organize(request, game_id)
            case "end":
                return self.post_end_operations(request, game_id)
            case _:
                return Response(
                    {"error": "Invalid route"}, status=status.HTTP_404_NOT_FOUND
                )

    def post_operation(self, request, game_id: int):
        operation = request.data["operation"]

        match operation:
            case "":
                try:
                    end_evening_operations(self.player(request, game_id))
                except ValueError as e:
                    raise ValidationError({"detail": str(e)})
                return self.generate_completed_step()

            case "recruit":
                return self.generate_step(
                    "recruit",
                    "Select clearing to recruit in, or cancel to select another operation.",
                    "recruit",
                    [
                        {"type": "clearing_number", "name": "clearing_number"},
                    ],
                )
            case "move":
                return self.generate_step(
                    "move",
                    "Select clearing to move from, or cancel to select another operation.",
                    "move-origin",
                    [
                        {"type": "clearing_number", "name": "origin_clearing_number"},
                    ],
                )

            case "battle":
                return self.generate_step(
                    "battle",
                    "Select clearing to battle in, or cancel to select another operation.",
                    "battle-clearing",
                    [
                        {"type": "clearing_number", "name": "clearing_number"},
                    ],
                )
            case "organize":
                return self.generate_step(
                    "organize",
                    "Select clearing to organize in, or cancel to select another operation.",
                    "organize",
                    [
                        {"type": "clearing_number", "name": "clearing_number"},
                    ],
                )
            case _:
                raise ValidationError("Invalid operation")

    def post_recruit(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_number = int(request.data["clearing_number"])
        try:
            clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        try:
            operation_recruit(player, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def post_move_origin(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_number = int(request.data["origin_clearing_number"])
        try:
            clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        try:
            validate_has_legal_moves(player, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        accumulated_payload = {"origin_clearing_number": clearing_number}
        return self.generate_step(
            "destination",
            f"Select destination clearing.",
            "move-destination",
            [
                {"type": "clearing_number", "name": "destination_clearing_number"},
            ],
            accumulated_payload,
        )

    def post_move_destination(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        origin_clearing_number = int(request.data["origin_clearing_number"])
        destination_clearing_number = int(request.data["destination_clearing_number"])
        try:
            origin_clearing = Clearing.objects.get(
                game=game, number=origin_clearing_number
            )
            destination_clearing = Clearing.objects.get(
                game=game, number=destination_clearing_number
            )
        except Clearing.DoesNotExist:
            raise ValidationError("Clearing does not exist")
        try:
            validate_legal_move(player, origin_clearing, destination_clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        accumulated_payload = {
            "origin_clearing_number": origin_clearing_number,
            "destination_clearing_number": destination_clearing_number,
        }

        return self.generate_step(
            "count",
            f"Select number of warriors to move.",
            "move-count",
            [
                {"type": "number", "name": "count"},
            ],
            accumulated_payload,
        )

    def post_move_count(self, request, game_id: int):
        player = self.player(request, game_id)
        origin_clearing_number = int(request.data["origin_clearing_number"])
        destination_clearing_number = int(request.data["destination_clearing_number"])
        count = int(request.data["count"])
        if count == 0:
            raise ValidationError("Must select at least one warrior to move, or cancel")
        try:
            origin_clearing = Clearing.objects.get(
                game=self.game(game_id), number=origin_clearing_number
            )
            destination_clearing = Clearing.objects.get(
                game=self.game(game_id), number=destination_clearing_number
            )
        except Clearing.DoesNotExist:
            raise ValidationError("Clearing does not exist")
        try:
            operation_move(player, origin_clearing, destination_clearing, count)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def post_battle_clearing(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        clearing_number = int(request.data["clearing_number"])
        try:
            clearing = Clearing.objects.get(game=game, number=clearing_number)
        except Clearing.DoesNotExist:
            raise ValidationError("Clearing does not exist")
        # check if valid clearing for battle
        if not player_has_warriors_in_clearing(player, clearing):
            raise ValidationError("Player does not have warriors in this clearing")
        try:
            validate_enemy_pieces_in_clearing(player, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        accumulated_payload = {"clearing_number": clearing_number}
        return self.generate_step(
            "defender",
            f"Select defender.",
            "battle-defender",
            [
                {"type": "faction", "name": "defender_faction"},
            ],
            accumulated_payload,
        )

    def post_battle_defender(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        clearing_number = int(request.data["clearing_number"])
        try:
            defender_faction = Faction[request.data["defender_faction"].upper()]
        except KeyError:
            raise ValidationError(
                f"Invalid faction: {request.data['defender_faction'].upper()}"
            )
        try:
            clearing = Clearing.objects.get(game=game, number=clearing_number)
        except Clearing.DoesNotExist:
            raise ValidationError("Clearing does not exist")
        try:
            defender = Player.objects.get(game=game, faction=defender_faction)
        except Player.DoesNotExist:
            raise ValidationError("Defending faction does not exist")
        try:
            operation_battle(player, defender, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def post_organize(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_number = int(request.data["clearing_number"])
        try:
            clearing = Clearing.objects.get(
                game=self.game(game_id), number=clearing_number
            )
        except Clearing.DoesNotExist:
            raise ValidationError("Clearing does not exist")
        try:
            operation_organize(player, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def post_end_operations(self, request, game_id: int):
        confirmation = bool(request.data["confirm"])
        if confirmation:
            try:
                end_evening_operations(self.player(request, game_id))
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        else:
            raise ValidationError("Invalid confirmation")

    def validate_timing(self, request, game_id, route, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        player = self.player(request, game_id)
        validate_step(player, WAEvening.WAEveningSteps.MILITARY_OPERATIONS)
