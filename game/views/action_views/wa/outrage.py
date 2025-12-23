from rest_framework.exceptions import ValidationError
from rest_framework.views import Response
from rest_framework import status

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Faction, Suit
from game.queries.wa.outrage import get_current_outrage_event
from game.transactions.wa import pay_outrage
from game.views.action_views.general import GameActionView


class OutrageView(GameActionView):
    name = "outrage"

    def initial(self, request, *args, **kwargs):
        # get game id for either post or get
        game_id = kwargs.get("game_id")
        if game_id is None:
            game_id = int(request.query_params.get("game_id"))
        # get faction by looking up outrage event
        try:
            outrage = get_current_outrage_event(self.game(game_id))
        except ValueError:
            raise ValidationError("Not the correct step")
        self.faction = Faction(outrage.outrageous_player.faction)

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        game = self.game(game_id)
        outrage = get_current_outrage_event(game)
        print((f"outrage_suit: {outrage.suit}"))
        suit = Suit(outrage.suit).label
        prompt = f"Play a card of suit {suit} to pay the outrage."
        # assert type(self.faction) == Faction
        print(f"faction: {self.faction}")
        self.first_step = {
            "faction": self.faction.label,
            "name": "card",
            "prompt": prompt,
            "endpoint": "card",
            "payload_details": [
                {"type": "card", "name": "card"},
            ],
        }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "card":
                return self.post_card(request, game_id)
            case _:
                return Response(
                    {"detail": "Invalid route"}, status=status.HTTP_404_NOT_FOUND
                )

    def post_card(self, request, game_id: int):
        card_name = request.data["card"]
        game = self.game(game_id)
        outrage = get_current_outrage_event(game)
        try:
            card = CardsEP[card_name]
        except KeyError:
            raise ValidationError("Invalid card")
        try:
            pay_outrage(outrage, card)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not the correct step"""
        game = self.game(game_id)
        try:
            outrage = get_current_outrage_event(game)
        except ValueError:
            raise ValidationError("Not the correct step")
