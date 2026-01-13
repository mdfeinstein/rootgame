from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.cats.turn import CatEvening
from game.models.game_models import Faction
from game.queries.cats.turn import get_phase
from game.queries.general import (
    get_current_player,
    get_player_hand_size,
    validate_player_has_card_in_hand,
)
from game.transactions.cats import cat_end_turn, cat_evening_draw, cat_discard_card
from game.decorators.transaction_decorator import atomic_game_action
from game.transactions.general import discard_card_from_hand
from game.views.action_views.general import GameActionView
from rest_framework.exceptions import ValidationError
from rest_framework.views import Response
from rest_framework import status
from django.db import transaction


class CatsDrawCardsView(GameActionView):
    action_name = "CATS_DRAW_CARDS"
    faction = Faction.CATS

    first_step = {
        "faction": faction.label,
        "name": "draw_cards",
        "prompt": "Confirm to draw cards",
        "endpoint": "evening-draw-cards",
        "payload_details": [{"type": "confirm", "name": "confirm"}],
        "options": [
            {"value": "confirm", "label": "Confirm"},
        ],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "evening-draw-cards":
            return self.post_draw_cards(request, game_id)
        return Response({"error": "Invalid route"}, status=status.HTTP_404_NOT_FOUND)

    def post_draw_cards(self, request, game_id: int):
        confirmation = bool(request.data["confirm"])
        if not confirmation:
            raise ValidationError("Confirmation not provided")
        try:
            atomic_game_action(cat_evening_draw)(self.player(request, game_id))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        player = get_current_player(self.game(game_id))
        if player != self.player(request, game_id):
            raise ValidationError("Not this player's turn")
        evening = get_phase(self.player(request, game_id))
        if type(evening) != CatEvening:
            raise ValidationError("Not Evening phase")
        if evening.step != CatEvening.CatEveningSteps.DRAWING:  # type: ignore
            raise ValidationError("Not Drawing step")


class CatsDiscardCardsView(GameActionView):
    action_name = "CATS_DISCARD_CARDS"
    faction = Faction.CATS

    def get(self, request):
        # check how many cards need to be discarded
        game_id = int(request.query_params.get("game_id"))
        player = self.player(request, game_id)
        discard_cards = get_player_hand_size(player) - 5
        if discard_cards <= 0:
            # shouldnt be able to reach here but who knows
            return self.generate_completed_step()
        assert type(self.faction) == Faction
        self.first_step = {
            "faction": self.faction.label,
            "name": "discard_card",
            "prompt": f"select card to discard. Number to discard: {discard_cards}",
            "endpoint": "discard-cards",
            "payload_details": [{"type": "card", "name": "card_to_discard"}],
        }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        if route == "discard-cards":
            return self.post_discard_cards(request, game_id)
        return Response({"error": "Invalid route"}, status=status.HTTP_404_NOT_FOUND)

    def post_discard_cards(self, request, game_id: int):
        card_to_discard = CardsEP[request.data["card_to_discard"]]
        if card_to_discard == "":
            raise ValidationError("No card selected")

        try:
            atomic_game_action(cat_discard_card)(self.player(request, game_id), card_to_discard)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        cards_left_to_discard = get_player_hand_size(self.player(request, game_id)) - 5
        if cards_left_to_discard <= 0:
            return self.generate_completed_step()
        return self.generate_step(
            "discard_card",
            f"Select card to discard. Number to discard: {cards_left_to_discard}",
            "discard-cards",
            [{"type": "card", "name": "card_to_discard"}],
        )

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        player = get_current_player(self.game(game_id))
        if player != self.player(request, game_id):
            raise ValidationError("Not this player's turn")
        evening = get_phase(self.player(request, game_id))
        if type(evening) != CatEvening:
            raise ValidationError("Not Evening phase")
        if evening.step != CatEvening.CatEveningSteps.DISCARDING:  # type: ignore
            raise ValidationError("Not Discarding step")
