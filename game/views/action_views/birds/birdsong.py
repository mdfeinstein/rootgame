from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.player import DecreeEntry
from game.models.birds.turn import BirdBirdsong
from game.models.game_models import Faction
from game.queries.birds.decree import (
    get_bird_added_to_decree,
    get_number_added_to_decree,
    validate_card_to_decree,
)
from game.queries.birds.turn import get_phase
from game.queries.general import get_current_player, validate_player_has_card_in_hand
from game.transactions.birds import (
    add_card_to_decree,
    emergency_draw,
    end_add_to_decree_step,
)
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
        "options": [
            {"value": "confirm", "label": "Confirm"},
        ],
    }

    def route_post(self, request, game_id: int, route: int, *args, **kwargs):
        if route == "confirm":
            return self.post_confirm(request, game_id, *args, **kwargs)
        else:
            raise ValueError("Invalid route. valid routes: confirm")

    def post_confirm(self, request, game_id: int, *args, **kwargs):
        """confirms the emergency drawing step"""
        print(request.data["confirm"])
        if not request.data["confirm"]:
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

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        try:
            num_added = get_number_added_to_decree(
                self.player_by_faction(request, game_id)
            )
            bird_added = get_bird_added_to_decree(
                self.player_by_faction(request, game_id)
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        ordinal = "first" if num_added == 0 else "second"
        bird_added_str = " Bird card has been added already." if bird_added else ""
        return self.generate_step(
            "card",
            f"Select {ordinal} card to add to the Decree. You must pick one card.{bird_added_str}"
            + "Or, choose nothing to end add to decree step.",
            "card",
            [
                {"type": "card", "name": "card_to_add"},
            ],
            options=[
                {"value": "", "label": "Done"},
            ],
        )

    def route_post(self, request, game_id: int, route: str):
        if route == "card":
            return self.post_card(request, game_id)
        elif route == "column":
            return self.post_column(request, game_id)
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
            try:
                end_add_to_decree_step(self.player(request, game_id))
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        card_name = request.data["card_to_add"]
        card = CardsEP[card_name]
        # check that card selected may be added to decree
        try:
            validate_card_to_decree(self.player(request, game_id), card)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        options = [
            {"value": column.name, "label": column.label}
            for column in DecreeEntry.Column
        ]
        return self.generate_step(
            "select_decree_column",
            "Select a Decree column to add to",
            "column",
            [
                {"type": "decree_column", "name": "decree_column"},
            ],
            {"card_to_add": card_name},
            options=options,
        )

    def post_column(self, request, game_id: int):
        column_name = request.data["decree_column"]
        column = DecreeEntry.Column[column_name]
        player = self.player(request, game_id)
        card = CardsEP[request.data["card_to_add"]]
        # add to decree
        try:
            add_card_to_decree(player, card, column)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # complete process. if there is another card to add, we will be redirected to that step
        return self.generate_completed_step()
