from game.decorators.transaction_decorator import atomic_game_action
from game.models.birds.player import BirdLeader
from game.models.birds.setup import BirdsSimpleSetup
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import Clearing, Faction, Game, Player
from game.queries.setup.birds import validate_corner
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
    faction = Faction.BIRDS
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

    def route_post(self, request, game_id: int, route: str):
        if route == "corner":
            return self.post_corner(request, game_id)
        return Response({"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST)

    def post_corner(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        # check that corner is valid
        clearing_number = int(request.data["corner_clearing_number"])
        try:
            clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        try:
            atomic_game_action(pick_corner)(player, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # serialize the next step
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        game = self.game(game_id)
        player = self.player(request, game_id)
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
    faction = Faction.BIRDS
    faction_string = Faction.BIRDS.label
    first_step = {
        "faction": faction_string,
        "name": "select_leader",
        "prompt": "Select leader",
        "endpoint": "leader",
        "payload_details": [{"type": "leader", "name": "leader"}],
        "options": [
            {"label": leader.label, "value": leader.name}
            for leader in BirdLeader.BirdLeaders
        ],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "leader":
            return self.post_leader(request, game_id)
        return Response({"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST)

    def post_leader(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        leader_str = request.data["leader"]
        # check that leader is valid
        try:
            leader = BirdLeader.BirdLeaders[leader_str]
        except KeyError:
            raise ValidationError({"detail": f"Invalid leader: {leader_str}"})
        try:
            atomic_game_action(choose_leader_initial)(player, leader)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        game = self.game(game_id)
        player = self.player(request, game_id)
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
    faction = Faction.BIRDS
    faction_string = Faction.BIRDS.label

    first_step = {
        "faction": faction_string,
        "name": "confirm",
        "prompt": "Confirm completed setup",
        "endpoint": "confirm",
        "payload_details": [{"type": "confirm", "name": "confirm"}],
        "options": [
            {"label": "Confirm", "value": True},
        ],
    }

    def route_post(self, request, game_id: int, route: str):
        if route != "confirm":
            raise ValidationError("Invalid route")
        player = self.player(request, game_id)
        try:
            atomic_game_action(confirm_completed_setup, undoable=False)(player)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        game = self.game(game_id)
        player = self.player(request, game_id)
        game_setup = GameSimpleSetup.objects.get(game=game)
        if game_setup.status != GameSimpleSetup.GameSetupStatus.BIRDS_SETUP:
            raise ValidationError("Not this player's setup turn")
        birds_setup = BirdsSimpleSetup.objects.get(player=player)
        if birds_setup.step != BirdsSimpleSetup.Steps.PENDING_CONFIRMATION:
            raise ValidationError(
                {"detail": f"Wrong step. Current step: {birds_setup.step}"}
            )
