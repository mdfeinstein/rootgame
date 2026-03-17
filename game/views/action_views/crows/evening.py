from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from game.models.game_models import Clearing, Faction, Player
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowEvening
from game.queries.crows.turn import validate_step, validate_phase
from game.queries.general import get_player_hand_size, get_enemy_factions_in_clearing
from game.transactions.crows.evening import (
    do_exert_action,
    discard_card,
    check_discard_step,
)
from game.transactions.crows.turn import next_step
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.decorators.transaction_decorator import atomic_game_action
from game.views.action_views.general import GameActionView


class CrowsExertView(GameActionView):
    action_name = "CROWS_EXERT"
    faction = Faction.CROWS

    def get_first_step(self, player):
        evening = validate_phase(player, CrowEvening)
        return {
            "faction": self.faction.label,
            "name": "select_exert_action",
            "prompt": "You may exert to take one extra action (Plot, Trick, Move, or Battle). COST: You will draw NO cards at the end of this turn.",
            "endpoint": "action",
            "payload_details": [{"type": "action_type", "name": "action"}],
            "options": [
                {
                    "value": "plot",
                    "label": "Exert: Plot",
                    "info": "Place a facedown plot token by removing one warrior from this clearing, plus one warrior for each plot token placed this turn.",
                },
                {
                    "value": "trick",
                    "label": "Exert: Trick",
                    "info": "Swap two plot tokens, either both face up or face down.",
                },
                {"value": "move", "label": "Exert: Move", "info": "Move warriors."},
                {
                    "value": "battle",
                    "label": "Exert: Battle",
                    "info": "Initiate combat.",
                },
                {
                    "value": "skip",
                    "label": "Skip Exerting",
                    "info": "Do not exert this turn. You will draw cards normally.",
                },
            ],
        }

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        player = self.player_by_faction(request, game_id)
        self.first_step = self.get_first_step(player)
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "action":
                return self.post_action(request, game_id)
            case "plot-clearing":
                return self.post_plot_clearing(request, game_id)
            case "plot-type":
                return self.post_plot_type(request, game_id)
            case "trick-1":
                return self.post_trick_1(request, game_id)
            case "trick-2":
                return self.post_trick_2(request, game_id)
            case "move-origin":
                return self.post_move_origin(request, game_id)
            case "move-destination":
                return self.post_move_destination(request, game_id)
            case "move-count":
                return self.post_move_count(request, game_id)
            case "battle-clearing":
                return self.post_battle_clearing(request, game_id)
            case "battle-faction":
                return self.post_battle_faction(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_action(self, request, game_id: int):
        player = self.player(request, game_id)
        action = request.data["action"]
        if action == "skip":
            try:
                atomic_game_action(next_step)(player)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        match action:
            case "plot":
                return self.generate_step(
                    "plot_clearing",
                    "Select clearing to plot in.",
                    "plot-clearing",
                    [{"type": "clearing_number", "name": "clearing_number"}],
                )
            case "trick":
                return self.generate_step(
                    "trick_1",
                    "Select first plot token to trick.",
                    "trick-1",
                    [{"type": "clearing_number", "name": "clearing_number"}],
                )
            case "move":
                return self.generate_step(
                    "move_origin",
                    "Select origin clearing for move.",
                    "move-origin",
                    [{"type": "clearing_number", "name": "clearing_number"}],
                )
            case "battle":
                return self.generate_step(
                    "battle_clearing",
                    "Select clearing to battle in.",
                    "battle-clearing",
                    [{"type": "clearing_number", "name": "clearing_number"}],
                )
            case _:
                raise ValidationError("Invalid action type")

    # Reusing Daylight styles but calling do_exert_action

    # PLOT
    def post_plot_clearing(self, request, game_id: int):
        clearing_number = int(request.data["clearing_number"])
        return self.generate_step(
            "plot_type",
            "Select plot type to place.",
            "plot-type",
            [{"type": "plot_type", "name": "plot_type"}],
            {"clearing_number": clearing_number},
        )

    def post_plot_type(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_num = request.data["clearing_number"]
        plot_type = request.data["plot_type"]
        clearing = Clearing.objects.get(
            game=self.game(game_id), clearing_number=clearing_num
        )
        try:
            atomic_game_action(do_exert_action)(
                player, "plot", clearing=clearing, plot_type=plot_type
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    # TRICK
    def post_trick_1(self, request, game_id: int):
        clearing_number = int(request.data["clearing_number"])
        return self.generate_step(
            "trick_2",
            "Select second plot token to trick.",
            "trick-2",
            [{"type": "clearing_number", "name": "clearing_number"}],
            {"plot1_clearing": clearing_number},
        )

    def post_trick_2(self, request, game_id: int):
        player = self.player(request, game_id)
        p1_clearing_num = request.data["plot1_clearing"]
        p2_clearing_num = int(request.data["clearing_number"])
        try:
            p1 = PlotToken.objects.get(
                player=player, clearing__clearing_number=p1_clearing_num
            )
            p2 = PlotToken.objects.get(
                player=player, clearing__clearing_number=p2_clearing_num
            )
            atomic_game_action(do_exert_action)(player, "trick", plot1=p1, plot2=p2)
        except (PlotToken.DoesNotExist, ValueError) as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    # MOVE
    def post_move_origin(self, request, game_id: int):
        clearing_number = int(request.data["clearing_number"])
        return self.generate_step(
            "move_destination",
            "Select destination clearing.",
            "move-destination",
            [{"type": "clearing_number", "name": "clearing_number"}],
            {"origin_clearing": clearing_number},
        )

    def post_move_destination(self, request, game_id: int):
        origin_num = request.data["origin_clearing"]
        dest_num = int(request.data["clearing_number"])
        return self.generate_step(
            "move_count",
            "Select number of warriors to move.",
            "move-count",
            [{"type": "number", "name": "count"}],
            {"origin_clearing": origin_num, "destination_clearing": dest_num},
        )

    def post_move_count(self, request, game_id: int):
        player = self.player(request, game_id)
        origin_num = request.data["origin_clearing"]
        dest_num = request.data["destination_clearing"]
        count = int(request.data["count"])
        game = self.game(game_id)
        origin = Clearing.objects.get(game=game, clearing_number=origin_num)
        dest = Clearing.objects.get(game=game, clearing_number=dest_num)
        try:
            atomic_game_action(do_exert_action)(
                player, "move", origin=origin, destination=dest, count=count
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    # BATTLE
    def post_battle_clearing(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_number = int(request.data["clearing_number"])
        clearing = Clearing.objects.get(
            game=self.game(game_id), clearing_number=clearing_number
        )
        enemy_factions = get_enemy_factions_in_clearing(player, clearing)
        options = [
            {
                "value": f.name,
                "label": f.label,
                "info": f"Initiate battle against the {f.label}.",
            }
            for f in enemy_factions
        ]
        return self.generate_step(
            "battle_faction",
            "Select faction to battle.",
            "battle-faction",
            [{"type": "faction", "name": "defender_faction"}],
            {"clearing_number": clearing_number},
            options=options,
        )

    def post_battle_faction(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_num = request.data["clearing_number"]
        defender_faction = request.data["defender_faction"]
        clearing = Clearing.objects.get(
            game=self.game(game_id), clearing_number=clearing_num
        )
        try:
            atomic_game_action(do_exert_action)(
                player, "battle", defender_faction=defender_faction, clearing=clearing
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, CrowEvening.CrowEveningSteps.EXERT)


class CrowsDiscardingView(GameActionView):
    action_name = "CROWS_DISCARD_CARDS"
    faction = Faction.CROWS

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        player = self.player(request, game_id)
        discard_count = get_player_hand_size(player) - 5
        if discard_count <= 0:
            try:
                atomic_game_action(check_discard_step)(player)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        self.first_step = {
            "faction": self.faction.label,
            "name": "discard_card",
            "prompt": f"Select card to discard. Cards to discard: {discard_count}",
            "endpoint": "discard",
            "payload_details": [{"type": "card", "name": "card_to_discard"}],
        }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        if route == "discard":
            return self.post_discard(request, game_id)
        raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_discard(self, request, game_id: int):
        player = self.player(request, game_id)
        card_name = request.data["card_to_discard"]
        if not card_name:
            raise ValidationError("No card selected")
        card = CardsEP[card_name]
        try:
            atomic_game_action(discard_card)(player, card)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        discard_count = get_player_hand_size(player) - 5
        if discard_count <= 0:
            return self.generate_completed_step()

        return self.generate_step(
            "discard_card",
            f"Select card to discard. Cards to discard: {discard_count}",
            "discard",
            [{"type": "card", "name": "card_to_discard"}],
        )

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, CrowEvening.CrowEveningSteps.DISCARDING)
