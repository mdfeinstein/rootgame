from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Faction, Suit
from game.queries.cats.field_hospital import get_field_hospital_event
from game.transactions.cats import cat_resolve_field_hospital
from game.views.action_views.general import GameActionView
from rest_framework.exceptions import ValidationError
from rest_framework.views import Response
from rest_framework import status


class FieldHospitalView(GameActionView):
    name = "field_hospital"
    faction = Faction.CATS

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        player = self.player(request, game_id)
        field_hospital_event = get_field_hospital_event(player)
        count, suit = (
            field_hospital_event.troops_To_save,
            Suit(field_hospital_event.suit).label,
        )
        prompt = f"Play a card of suit {suit} to save {count} troops and place them at your keep."

        self.first_step = {
            "faction": self.faction.label,
            "name": "card",
            "prompt": prompt,
            "endpoint": "card",
            "payload_details": [
                {"type": "card", "name": "card"},
            ],
            "options": [
                {"value": "", "label": "Decline"},
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
        player = self.player(request, game_id)
        if card_name == "":
            card = None
        else:
            try:
                card = CardsEP[card_name]
            except KeyError:
                raise ValidationError("Invalid card")
        try:
            atomic_game_action(cat_resolve_field_hospital)(player, card)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not the correct step"""
        game = self.game(game_id)
        try:
            get_field_hospital_event(self.player(request, game_id))
        except ValueError:
            raise ValueError("Not the correct step")
