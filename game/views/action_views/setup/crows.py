from game.decorators.transaction_decorator import atomic_game_action
from game.models.crows.setup import CrowsSimpleSetup
from game.models.game_models import Clearing, Faction, Game, Player
from game.transactions.crows_setup import (
    confirm_completed_setup,
    place_initial_warrior,
)
from ..general import GameActionView
from rest_framework.exceptions import ValidationError
from rest_framework.views import Response
from rest_framework import status


class CrowsPickClearingView(GameActionView):
    action_name = "CROWS_PICK_CLEARING"
    faction = Faction.CROWS
    faction_string = Faction.CROWS.label

    def get(self, request, *args, **kwargs):
        game_id = kwargs.get("game_id") or request.query_params.get("game_id")
        player = self.player(request, game_id)
        setup = CrowsSimpleSetup.objects.get(player=player)

        prompt = "Place a warrior in a Fox, Rabbit, and Mouse clearing (one each)."
        if setup.fox_placed and setup.rabbit_placed:
            prompt = "Place a warrior in a Mouse clearing."
        elif setup.fox_placed and setup.mouse_placed:
            prompt = "Place a warrior in a Rabbit clearing."
        elif setup.rabbit_placed and setup.mouse_placed:
            prompt = "Place a warrior in a Fox clearing."
        elif setup.fox_placed:
            prompt = "Place a warrior in a Rabbit or Mouse clearing."
        elif setup.rabbit_placed:
            prompt = "Place a warrior in a Fox or Mouse clearing."
        elif setup.mouse_placed:
            prompt = "Place a warrior in a Fox or Rabbit clearing."

        return self.generate_step(
            name="pick_clearing",
            prompt=prompt,
            endpoint="clearing",
            payload_details=[{"type": "clearing_number", "name": "clearing_number"}],
            faction=Faction.CROWS,
        )

    def route_post(self, request, game_id: int, route: str):
        if route == "clearing":
            return self.post_clearing(request, game_id)
        return Response({"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST)

    def post_clearing(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        clearing_number = int(request.data["clearing_number"])
        try:
            clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})

        try:
            atomic_game_action(place_initial_warrior)(player, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        setup = CrowsSimpleSetup.objects.get(player=player)
        if setup.step != CrowsSimpleSetup.Steps.WARRIOR_PLACE:
            raise ValidationError({"detail": "Not in warrior placement step"})


class CrowsConfirmCompletedSetupView(GameActionView):
    action_name = "CROWS_CONFIRM_COMPLETED_SETUP"
    faction = Faction.CROWS
    faction_string = Faction.CROWS.label

    first_step = {
        "faction": faction_string,
        "name": "confirm",
        "prompt": "Confirm completed setup",
        "endpoint": "confirm",
        "payload_details": [{"type": "confirm", "name": "confirm"}],
        "options": [{"value": True, "label": "Confirm"}],
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
        player = self.player(request, game_id)
        setup = CrowsSimpleSetup.objects.get(player=player)
        if setup.step != CrowsSimpleSetup.Steps.PENDING_CONFIRMATION:
            raise ValidationError({"detail": "Setup not complete"})
