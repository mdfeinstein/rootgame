from game.models.birds.player import BirdLeader
from game.models.birds.setup import BirdsSimpleSetup
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import Clearing, Faction, Game, Player
from game.serializers.general_serializers import GameActionStepSerializer
from game.transactions.birds_setup import (
    choose_leader_initial,
    confirm_completed_setup,
    pick_corner,
)
from game.utility.textchoice import get_choice_value_by_label_or_value
from game.views.action_views.general import GameActionView

from rest_framework.views import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError


class BirdsPickCornerView(GameActionView):
    action_name = "BIRDS_PICK_CORNER"
    faction_string = Faction.BIRDS.label
    first_step = {
        "faction": faction_string,
        "name": "select_corner",
        "prompt": "Select corner clearing for your roost and six warriors. "
        + "If cat's keep is in play, it must be opposite the keep.",
        "endpoint": "corner",
        "payload_details": [
            {"type": "clearing_number", "name": "corner_clearing_number"}
        ],
    }

    def post(self, request, game_id: int, route: str):
        if route == "corner":
            return self.post_corner(request, game_id)
        elif route == "confirm":
            return self.post_confirm(request, game_id)
        return Response({"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST)

    def post_corner(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        self.validate_timing(game, player)
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
                "prompt": "Confirm corner clearing choice",
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
        self.validate_timing(game, player)
        try:
            clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        # TODO: these should probably be atomic together.
        try:
            pick_corner(player, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # need formal way to signal action completed, look for next action
        return Response({"name": "completed"})

    def validate_timing(self, game: Game, player: Player):
        """raises if not this player's turn or correct step"""
        game_setup = GameSimpleSetup.objects.get(game=game)
        if game_setup.status != GameSimpleSetup.GameSetupStatus.BIRDS_SETUP:
            raise ValidationError("Not this player's setup turn")
        birds_setup = BirdsSimpleSetup.objects.get(player=player)
        if birds_setup.step != BirdsSimpleSetup.Steps.PICKING_CORNER:
            raise ValidationError(
                {"detail": f"Wrong step. Current step: {birds_setup.step}"}
            )


class BirdsChooseLeaderInitialView(GameActionView):
    action_name = "BIRDS_CHOOSE_LEADER_INITIAL"
    faction_string = Faction.BIRDS.label
    first_step = {
        "faction": faction_string,
        "name": "select_leader",
        "prompt": "Select leader",
        "endpoint": "leader",
        "payload_details": [{"type": "leader", "name": "leader"}],
    }

    def post(self, request, game_id: int, route: str):
        if route == "leader":
            return self.post_leader(request, game_id)
        elif route == "confirm":
            return self.post_confirm(request, game_id)
        return Response({"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST)

    def post_leader(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        self.validate_timing(game, player)
        leader = request.data["leader"]
        # check that leader is valid
        try:
            leader_value = get_choice_value_by_label_or_value(
                BirdLeader.BirdLeaders, leader.capitalize()
            )
        except ValueError:
            raise ValidationError({"detail": f"Invalid leader: {leader}"})

        # serialize the next step
        serializer = GameActionStepSerializer(
            {
                "faction": self.faction_string,
                "name": "confirm",
                "prompt": "Confirm leader choice",
                "endpoint": "confirm",
                "payload_details": [{"type": "confirm", "name": "confirm"}],
                "accumulated_payload": {
                    "leader": leader,
                },
            }
        )
        return Response(serializer.data)

    def post_confirm(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        self.validate_timing(game, player)
        confirmation = bool(request.data["confirm"])
        if not confirmation:
            # client will reset and check for its next options.
            return Response({"name": "canceled"})
        leader = request.data["leader"]
        leader_choice = None
        leader_value = get_choice_value_by_label_or_value(
            BirdLeader.BirdLeaders, leader.capitalize()
        )
        choose_leader_initial(player, BirdLeader.BirdLeaders(leader_value))
        return Response({"name": "completed"})

    def validate_timing(self, game: Game, player: Player):
        """raises if not this player's turn or correct step"""
        game_setup = GameSimpleSetup.objects.get(game=game)
        if game_setup.status != GameSimpleSetup.GameSetupStatus.BIRDS_SETUP:
            raise ValidationError("Not this player's setup turn")
        birds_setup = BirdsSimpleSetup.objects.get(player=player)
        if birds_setup.step != BirdsSimpleSetup.Steps.CHOOSING_LEADER:
            raise ValidationError(
                {"detail": f"Wrong step. Current step: {birds_setup.step}"}
            )


class BirdsConfirmCompletedSetupView(GameActionView):
    action_name = "BIRDS_CONFIRM_COMPLETED_SETUP"
    faction_string = Faction.BIRDS.label

    first_step = {
        "faction": faction_string,
        "name": "confirm",
        "prompt": "Confirm completed setup",
        "endpoint": "confirm",
        "payload_details": [{"type": "confirm", "name": "confirm"}],
    }

    def post(self, request, game_id: int, route: str):
        if route != "confirm":
            raise ValidationError("Invalid route")
        game = self.game(game_id)
        player = self.player(request, game_id)
        self.validate_timing(game, player)
        try:
            confirm_completed_setup(player)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return Response({"name": "completed"})

    def validate_timing(self, game: Game, player: Player):
        """raises if not this player's turn or correct step"""
        game_setup = GameSimpleSetup.objects.get(game=game)
        if game_setup.status != GameSimpleSetup.GameSetupStatus.BIRDS_SETUP:
            raise ValidationError("Not this player's setup turn")
        birds_setup = BirdsSimpleSetup.objects.get(player=player)
        if birds_setup.step != BirdsSimpleSetup.Steps.PENDING_CONFIRMATION:
            raise ValidationError(
                {"detail": f"Wrong step. Current step: {birds_setup.step}"}
            )
