from game.queries.general import validate_can_activate_dominance
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from game.models import Player, Card, Suit
from game.models.dominance import DominanceSupplyEntry, ActiveDominanceEntry
from game.models.game_models import HandEntry
from game.transactions.dominance import swap_dominance, activate_dominance
from game.views.action_views.general import GameActionView
from game.queries.general import (
    is_phase,
    validate_player_has_card_in_hand,
    validate_game_has_dominance_card_in_supply,
)
from game.game_data.cards.exiles_and_partisans import CardsEP


class SwapDominanceView(GameActionView):
    action_name = "SWAP_DOMINANCE"

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        game = self.game(game_id)

        # Get available dominance cards
        supply_entries = DominanceSupplyEntry.objects.filter(game=game)
        options = []
        for entry in supply_entries:
            options.append(
                {
                    "value": entry.card.card_type,
                    "label": Suit(entry.card.suit).label,
                }
            )

        return self.generate_step(
            name="select_dominance",
            prompt="Select a dominance card to swap for.",
            endpoint="select_dominance",
            payload_details=[{"type": "option", "name": "dominance_card_name"}],
            options=options,
        )

    def route_post(self, request, game_id: int, route: str, *args, **kwargs):
        if route == "select_dominance":
            return self.post_select_dominance(request, game_id)
        elif route == "swap":
            return self.post_swap(request, game_id)
        else:
            raise ValidationError("Invalid route")

    def post_select_dominance(self, request, game_id: int):
        player = self.player(request, game_id)
        dominance_card_name = request.data.get("dominance_card_name")

        # Validate dominance card exists in supply
        try:
            dominance_card_enum = CardsEP[dominance_card_name]
            dominance_entry = validate_game_has_dominance_card_in_supply(
                player.game, dominance_card_enum
            )
        except (KeyError, ValueError):
            raise ValidationError("Dominance card not available in supply.")

        dominance_suit = dominance_entry.card.suit

        # Get matching cards in hand
        # Can match suit or be a bird
        hand_cards = HandEntry.objects.filter(player=player)
        options = []
        for entry in hand_cards:
            if entry.card.suit == Suit.WILD or entry.card.suit == dominance_suit:
                options.append(
                    {
                        "value": entry.card.card_type,
                        "label": entry.card.title,
                    }
                )

        if not options:
            raise ValidationError("You do not have a matching card to swap.")

        return self.generate_step(
            name="swap",
            prompt=f"Select a card to discard for {dominance_entry.card.title}",
            endpoint="swap",
            payload_details=[
                {"type": "card", "name": "card_to_discard_name"},
            ],
            accumulated_payload={"dominance_card_name": dominance_card_name},
            options=options,
        )

    def post_swap(self, request, game_id: int):
        player = self.player(request, game_id)
        dominance_card_name = request.data.get("dominance_card_name")
        card_to_discard_name = request.data.get("card_to_discard_name")

        try:
            dominance_card_enum = CardsEP[dominance_card_name]
            card_to_discard_enum = CardsEP[card_to_discard_name]

            dominance_entry = validate_game_has_dominance_card_in_supply(
                player.game, dominance_card_enum
            )
            card_in_hand_entry = validate_player_has_card_in_hand(
                player, card_to_discard_enum
            )

            swap_dominance(player, card_in_hand_entry, dominance_entry)
        except (KeyError, ValueError) as e:
            raise ValidationError(str(e))

        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, route: str, *args, **kwargs):
        player = self.player(request, game_id)
        if not is_phase(player, "Daylight"):
            raise ValidationError("Must be in Daylight to swap dominance.")


class ActivateDominanceView(GameActionView):
    action_name = "ACTIVATE_DOMINANCE"

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        player = self.player(request, game_id)
        try:
            validate_can_activate_dominance(player)
        except ValidationError as e:
            raise {"detail": str(e)}
        # provide dominance cards in hand as options
        all_hand = HandEntry.objects.filter(player=player)
        options = []
        for entry in all_hand:
            if entry.card.dominance:
                options.append(
                    {
                        "value": entry.card.card_type,
                        "label": entry.card.title,
                    }
                )

        if not options:
            # Should probably not happen if button only active when valid, but handle gracefullly
            raise ValidationError({"detail": "No dominance cards in hand."})

        return self.generate_step(
            name="activate",
            prompt="Select dominance card to activate.",
            endpoint="activate",
            payload_details=[{"type": "card", "name": "card_in_hand_name"}],
            options=options,
        )

    def route_post(self, request, game_id: int, route: str, *args, **kwargs):
        if route == "activate":
            return self.post_activate(request, game_id)
        raise ValidationError("Invalid route")

    def post_activate(self, request, game_id: int):
        player = self.player(request, game_id)
        card_in_hand_name = request.data.get("card_in_hand_name")

        try:
            card_enum = CardsEP[card_in_hand_name]
            card_in_hand = validate_player_has_card_in_hand(player, card_enum)
            activate_dominance(player, card_in_hand)
        except (KeyError, ValueError) as e:
            raise ValidationError(str(e))

        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, route: str, *args, **kwargs):
        player = self.player(request, game_id)
        # "During your Daylight"
        if not is_phase(player, "Daylight"):
            raise ValidationError("Must be in Daylight to activate dominance.")
