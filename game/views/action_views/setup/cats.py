from game.queries.general import available_building_slot
from game.models.cats.buildings import CatBuildingTypes
from game.models.cats.setup import CatsSimpleSetup
from game.models.cats.tokens import CatKeep
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import Clearing, Faction, Game, Player
from game.queries.setup.cats import (
    validate_building_type,
    validate_keep_is_here_or_adjacent,
    validate_timing,
)
from game.serializers.general_serializers import (
    GameActionSerializer,
    GameActionStepSerializer,
)
from game.transactions.cats_setup import (
    confirm_completed_setup,
    pick_corner,
    place_initial_building,
    place_garrison,
)
from ..general import GameActionView
from rest_framework.exceptions import ValidationError
from rest_framework.views import Response
from rest_framework import status


class CatsPickCornerView(GameActionView):
    action_name = "CATS_PICK_CORNER"
    faction = Faction.CATS
    faction_string = Faction.CATS.label
    first_step = {
        "faction": faction_string,
        "name": "select_corner",
        "prompt": "Select corner clearing for your keep",
        "endpoint": "corner",
        "payload_details": [
            {"type": "clearing_number", "name": "corner_clearing_number"}
        ],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "corner":
            return self.post_corner(request, game_id)
        elif route == "confirm":
            return self.post_confirm(request, game_id)

        return Response({"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST)

    def post_corner(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        self.validate_timing(request, game_id)
        # check that corner is valid
        clearing_number = int(request.data["corner_clearing_number"])
        if clearing_number not in [1, 2, 3, 4]:
            raise ValidationError(
                {"detail": f"Invalid clearing number: {clearing_number}"}
            )
        # serialize the next step
        serializer = GameActionStepSerializer(
            {
                "faction": self.faction_string,
                "name": "confirm",
                "prompt": "Confirm keep corner clearing choice",
                "endpoint": "confirm",
                "payload_details": [{"type": "confirm", "name": "confirm"}],
                "accumulated_payload": {
                    "corner_clearing_number": clearing_number,
                },
            }
        )
        return Response(serializer.data)

    def post_confirm(self, request, game_id: int):
        game = self.game(game_id)
        clearing_number = int(request.data["corner_clearing_number"])
        player = self.player(request, game_id)
        confirmation = bool(request.data["confirm"])
        if not confirmation:
            # client will reset and check for its next options.
            return Response({"name": "canceled"})
        self.validate_timing(request, game_id)
        try:
            clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        # TODO: these should probably be atomic together.
        pick_corner(player, clearing)
        opposite_corner_number = ((clearing_number - 1 + 2) % 4) + 1
        opposite_corner = Clearing.objects.get(
            game=game, clearing_number=opposite_corner_number
        )
        place_garrison(player, opposite_corner)
        # need formal way to signal action completed, look for next action
        return Response({"name": "completed"})

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        try:
            validate_timing(
                self.player(request, game_id), CatsSimpleSetup.Steps.PICKING_CORNER
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})


class CatsPlaceBuildingView(GameActionView):
    faction = Faction.CATS
    faction_string = Faction.CATS.label
    action_name = "CATS_PLACE_BUILDING"
    first_step = {
        "faction": faction_string,
        "name": "select_clearing",
        "prompt": "Select clearing for initial building",
        "endpoint": "clearing",
        "payload_details": [
            {"type": "clearing_number", "name": "building_clearing_number"}
        ],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "clearing":
            return self.post_clearing(request, game_id)
        elif route == "building_type":
            return self.post_building_type(request, game_id)
        elif route == "confirm":
            return self.post_confirm(request, game_id)
        return Response({"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST)

    def post_clearing(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        clearing_number = int(request.data["building_clearing_number"])
        try:
            self.validate_clearing_number(clearing_number, game, player)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # serialize the next step
        serializer = GameActionStepSerializer(
            {
                "faction": self.faction_string,
                "name": "building_type",
                "prompt": "Select building type",
                "endpoint": "building_type",
                "payload_details": [{"type": "building_type", "name": "building_type"}],
                "accumulated_payload": {
                    "building_clearing_number": clearing_number,
                },
            }
        )
        return Response(serializer.data)

    def post_building_type(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        building_type: str = request.data["building_type"]
        # check that building type is valid
        self.validate_building_type(player, building_type)

        serializer = GameActionStepSerializer(
            {
                "faction": self.faction_string,
                "name": "confirm",
                "prompt": "Confirm building placement",
                "endpoint": "confirm",
                "payload_details": [{"type": "confirm", "name": "confirm"}],
                "accumulated_payload": {
                    "building_clearing_number": int(
                        request.data["building_clearing_number"]
                    ),
                    "building_type": building_type,
                },
            }
        )
        return Response(serializer.data)

    def post_confirm(self, request, game_id: int):

        confirmation = bool(request.data["confirm"])
        if not confirmation:
            # client will reset and check for its next options.
            return Response({"name": "canceled"})
        player = self.player(request, game_id)
        clearing_number = int(request.data["building_clearing_number"])
        building_type = request.data["building_type"]
        clearing = Clearing.objects.get(
            game=self.game(game_id), clearing_number=clearing_number
        )
        building_enum = CatBuildingTypes(building_type.capitalize())
        try:
            place_initial_building(player, clearing, building_enum)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return Response({"name": "completed"})

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        try:
            validate_timing(
                self.player(request, game_id), CatsSimpleSetup.Steps.PLACING_BUILDINGS
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

    def validate_building_type(self, player: Player, building_type: str):
        try:
            building_type_enum = CatBuildingTypes(building_type.capitalize())
        except ValueError:
            raise ValidationError({"detail": f"Invalid building type: {building_type}"})
        try:
            validate_building_type(player, building_type_enum)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

    def validate_clearing_number(
        self, clearing_number: int, game: Game, player: Player
    ):
        try:
            clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        # check that the clearing is adjacent to the keep or is the same as the keep
        validate_keep_is_here_or_adjacent(player, clearing)
        # check that there is a free building slot
        building_slot = available_building_slot(clearing)
        if building_slot is None:
            raise ValueError("No free building slots")


class CatsConfirmCompletedSetupView(GameActionView):
    action_name = "CATS_CONFIRM_COMPLETED_SETUP"
    faction = Faction.CATS
    faction_string = Faction.CATS.label

    first_step = {
        "faction": faction_string,
        "name": "confirm",
        "prompt": "Confirm completed setup",
        "endpoint": "confirm",
        "payload_details": [],
    }

    def route_post(self, request, game_id: int, route: str):
        if route != "confirm":
            raise ValidationError("Invalid route")
        player = self.player(request, game_id)
        try:
            confirm_completed_setup(player)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return Response({"name": "completed"})

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        try:
            validate_timing(
                self.player(request, game_id),
                CatsSimpleSetup.Steps.PENDING_CONFIRMATION,
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
