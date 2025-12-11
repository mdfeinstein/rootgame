from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.turn import BirdBirdsong
from game.models.game_models import Faction
from game.queries.birds.turn import get_phase
from game.queries.general import get_current_player, validate_player_has_card_in_hand
from game.transactions.birds import emergency_draw
from game.views.action_views.general import GameActionView
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView


class EmergencyDrawingView(GameActionView):
    name = "EMERGENCY_DRAWING"
    faction = Faction.BIRDS

    first_step = {
        "faction": Faction.BIRDS.label,
        "name": "confirm_draw",
        "prompt": "Please confirm to finish the emergency draw step.",
        "endpoint": "confirm",
        "payload_details": [{"type": "confirm", "name": "confirm"}],
    }

    def route_post(self, request, game_id: int, route: int, *args, **kwargs):
        if route == "confirm":
            return self.post_confirm(request, game_id, *args, **kwargs)
        else:
            raise ValueError("Invalid route. valid routes: confirm")

    def post_confirm(self, request, game_id: int, *args, **kwargs):
        """confirms the emergency drawing step"""
        if request.data["confirm"] != "confirm":
            raise ValidationError("Invalid confirmation")
        try:
            emergency_draw(self.player(request, game_id))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return Response({"name": "completed"})

    def validate_timing(self, request, game_id, *args, **kwargs):
        """checks if it is birds turn and if we are up to the emergency drawing step"""
        if get_current_player(self.game(game_id)) != self.player_by_request(
            request, game_id
        ):
            raise ValidationError("Not your turn")
        birdsong = get_phase(self.player_by_request(request, game_id))
        if type(birdsong) != BirdBirdsong:
            raise ValidationError("Not Birdsong phase")
        if birdsong.step != BirdBirdsong.BirdBirdsongSteps.EMERGENCY_DRAWING:
            raise ValidationError("Not Emergency Drawing step")


class AddToDecreeView(GameActionView):
    name = "ADD_TO_DECREE"
    faction = Faction.BIRDS

    first_step = {
        "faction": Faction.BIRDS.label,
        "name": "select_card",
        "prompt": "Select first card to add to the Decree. You must pick one card",
        "endpoint": "card",
        "payload_details": [{"type": "card", "name": "card_to_add"}],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "card":
            return self.post_card(request, game_id)
        elif route == "column":
            return self.post_column(request, game_id)
        elif route == "confirm":
            return self.post_confirm(request, game_id)
        else:
            raise ValueError("Invalid route")

    def validate_timing(self, request, game_id, *args, **kwargs):
        """checks if it is birds turn and if we are up to the add to decree step"""
        if get_current_player(self.game(game_id)) != self.player_by_request(
            request, game_id
        ):
            raise ValidationError("Not your turn")
        birdsong = get_phase(self.player_by_request(request, game_id))
        if type(birdsong) != BirdBirdsong:
            raise ValidationError("Not Birdsong phase")
        if birdsong.step != BirdBirdsong.BirdBirdsongSteps.ADD_TO_DECREE:
            raise ValidationError("Not Add to Decree step")

    def post_card(self, request, game_id: int):
        if request.data["card_to_add"] == "":
            raise ValidationError("No card selected")
        card_name = request.data["card_to_add"]
        card = CardsEP[card_name]
        # check that player has card in hand
        try:
            validate_player_has_card_in_hand(self.player(request, game_id), card)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
