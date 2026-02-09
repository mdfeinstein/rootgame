from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Faction
from game.models.wa.turn import WADaylight
from game.queries.wa.turn import validate_step
from game.transactions.wa import (
    add_officer,
    add_supporter,
    end_daylight_actions,
    training,
)
from game.views.action_views.general import GameActionView
from rest_framework.views import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from game.game_data.general.game_enums import Suit
from game.queries.wa.crafting import (
    is_able_to_be_crafted,
    validate_crafting_pieces_satisfy_requirements,
)
from game.queries.wa.tokens import sympathy_at_clearing_number
from game.transactions.wa import wa_craft_card


from game.decorators.transaction_decorator import atomic_game_action


class WADaylightActionsView(GameActionView):
    action_name = "WA_DAYLIGHT_ACTIONS"
    faction = Faction.WOODLAND_ALLIANCE

    first_step = {
        "faction": faction.label,
        "name": "select_action",
        "prompt": "Select action: craft, mobilize, or train. Or, choose nothing to end action step.",
        "endpoint": "action",
        "payload_details": [{"type": "action_type", "name": "action"}],
        "options": [
            {"value": "craft", "label": "Craft"},
            {"value": "mobilize", "label": "Mobilize"},
            {"value": "train", "label": "Train"},
            {"value": "", "label": "Done"},
        ],
    }

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "action":
                return self.post_action(request, game_id)
            case "craft-card":
                return self.post_craft_card(request, game_id)
            case "craft-piece":
                return self.post_craft_piece(request, game_id)
            case "mobilize":
                return self.post_mobilize(request, game_id)
            case "train":
                return self.post_train(request, game_id)
            case _:
                return Response(
                    {"error": "Invalid route"}, status=status.HTTP_404_NOT_FOUND
                )

    def post_action(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        action = request.data["action"]
        # if no action selected, end action step
        if action == "":
            try:
                atomic_game_action(end_daylight_actions)(player)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        # otherwise, route to action step
        match action:
            case "craft":
                return self.generate_step(
                    "craft",
                    "Select card to craft.",
                    "craft-card",
                    [
                        {"type": "card", "name": "card_to_craft"},
                    ],
                )
            case "mobilize":
                return self.generate_step(
                    "mobilize",
                    "Select card to mobilize (place in supporter stack) or cancel to select another action.",
                    "mobilize",
                    [
                        {"type": "card", "name": "card_to_mobilize"},
                    ],
                )
            case "train":
                return self.generate_step(
                    "train",
                    "Select card matching a base to train an officer, or cancel to select another action."
                    + " If no bases, can't train.",
                    "train",
                    [
                        {"type": "card", "name": "card_to_train"},
                    ],
                )
            case _:
                raise ValidationError("Invalid action")

    def post_craft_card(self, request, game_id: int):
        if request.data["card_to_craft"] == "":
            return Response(self.first_step, status=status.HTTP_200_OK)

        player = self.player(request, game_id)
        card = CardsEP[request.data["card_to_craft"]]

        if not is_able_to_be_crafted(player, card):
            raise ValidationError("Not enough crafting pieces to craft this card")

        suits_needed = [cost.label for cost in card.value.cost]
        prompt = f"Select {(suits_needed)} crafting pieces to craft this card."
        return self.generate_step(
            "select_pieces",
            prompt,
            "craft-piece",
            [{"type": "clearing_number", "name": "clearing_number"}],
            {
                "card_to_craft": request.data["card_to_craft"],
                "clearing_numbers": [],
            },
        )

    def post_craft_piece(self, request, game_id: int):
        player = self.player(request, game_id)
        card = CardsEP[request.data["card_to_craft"]]
        old_clearing_numbers = request.data["clearing_numbers"]
        new_clearing_number = int(request.data["clearing_number"])
        clearing_numbers = old_clearing_numbers + [new_clearing_number]

        try:
            sympathies = [
                sympathy_at_clearing_number(player, clearing_number)
                for clearing_number in clearing_numbers
            ]
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        try:
            all_pieces_satisfied = validate_crafting_pieces_satisfy_requirements(
                player, card, sympathies
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        if all_pieces_satisfied:
            # try to craft
            try:
                atomic_game_action(wa_craft_card)(player, card, sympathies)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        # otherwise, continue to select pieces
        suits_needed = [cost.label for cost in card.value.cost]
        suits_selected = [Suit(sympathy.clearing.suit).label for sympathy in sympathies]
        prompt = f"Select more crafting pieces. Needed: {suits_needed}. Selected: {suits_selected}"
        return self.generate_step(
            "select_pieces",
            prompt,
            "craft-piece",
            [{"type": "clearing_number", "name": "clearing_number"}],
            {
                "card_to_craft": request.data["card_to_craft"],
                "clearing_numbers": clearing_numbers,
            },
        )

    def post_mobilize(self, request, game_id: int):
        """places card in supporter stack"""
        player = self.player(request, game_id)
        card_name = request.data["card_to_mobilize"]
        try:
            card = CardsEP[card_name]
        except KeyError:
            raise ValidationError("Invalid card")
        try:
            atomic_game_action(add_supporter)(player, card)

        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def post_train(self, request, game_id: int):
        """spends card to place in officer box"""
        player = self.player(request, game_id)
        card_name = request.data["card_to_train"]
        try:
            card = CardsEP[card_name]
        except KeyError:
            raise ValidationError("Invalid card")
        try:
            atomic_game_action(training)(player, card)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id, route, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        player = self.player(request, game_id)
        validate_step(player, WADaylight.WADaylightSteps.ACTIONS)
