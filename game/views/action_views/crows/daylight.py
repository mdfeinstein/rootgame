from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from game.models.game_models import Clearing, Faction, Player
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowDaylight
from game.queries.crows.turn import validate_step, validate_phase
from game.queries.general import (
    warrior_count_in_clearing,
    get_enemy_factions_in_clearing,
)
from game.transactions.crows.daylight import (
    do_daylight_action,
    end_daylight_action_step,
)
from game.decorators.transaction_decorator import atomic_game_action
from game.views.action_views.general import GameActionView


class CrowsDaylightActionsView(GameActionView):
    action_name = "CROWS_DAYLIGHT_ACTIONS"
    faction = Faction.CROWS

    def get_first_step(self, player):
        daylight = validate_phase(player, CrowDaylight)
        actions_left = daylight.actions_remaining
        return {
            "faction": self.faction.label,
            "name": "select_action",
            "prompt": f"Select action (Actions remaining: {actions_left}), or choose nothing to end daylight.",
            "endpoint": "action",
            "payload_details": [{"type": "action_type", "name": "action"}],
            "options": [
                {
                    "value": "plot",
                    "label": "Plot",
                    "info": "Place a facedown plot token in a clearing by removing 1 warrior plus one for each other time plotted this turn.",
                },
                {
                    "value": "trick",
                    "label": "Trick",
                    "info": "Swap two plot tokens on the map, either both faceup or facedown.",
                },
                {
                    "value": "move",
                    "label": "Move",
                    "info": "Move warriors from one clearing to another adjacent one.",
                },
                {
                    "value": "battle",
                    "label": "Battle",
                    "info": "Initiate combat in a clearing.",
                },
                {"value": "", "label": "Done", "info": "Finish daylight actions."},
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
        if action == "":
            try:
                atomic_game_action(end_daylight_action_step)(player)
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

    # PLOT
    def post_plot_clearing(self, request, game_id: int):
        clearing_number = int(request.data["clearing_number"])
        player = self.player(request, game_id)

        # Get available plot types from reserve
        reserve_plots = PlotToken.objects.filter(player=player, clearing__isnull=True)
        available_types = sorted(list(set(p.plot_type for p in reserve_plots)))

        plot_info = {
            PlotToken.PlotType.BOMB: "When flipped, remove all enemy pieces in this clearing and remove this token.",
            PlotToken.PlotType.SNARE: "While face up, non-Corvid pieces cannot move out of or be placed in this clearing.",
            PlotToken.PlotType.EXTORTION: "When flipped, take a random card from each player with pieces in this clearing.",
            PlotToken.PlotType.RAID: "When removed, place one Corvid warrior in each adjacent clearing.",
        }

        options = [
            {
                "value": t,
                "label": t.capitalize(),
                "info": plot_info.get(t, f"Place a {t.capitalize()} plot token."),
            }
            for t in available_types
        ]

        return self.generate_step(
            "plot_type",
            "Select plot type to place.",
            "plot-type",
            [{"type": "plot_type", "name": "plot_type"}],
            {"clearing_number": clearing_number},
            options=options,
        )

    def post_plot_type(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_number = request.data["clearing_number"]
        plot_type = request.data["plot_type"]
        game = self.game(game_id)
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)

        try:
            atomic_game_action(do_daylight_action)(
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
        game = self.game(game_id)

        try:
            p1 = PlotToken.objects.get(
                player=player, clearing__clearing_number=p1_clearing_num
            )
            p2 = PlotToken.objects.get(
                player=player, clearing__clearing_number=p2_clearing_num
            )
        except PlotToken.DoesNotExist:
            raise ValidationError("Could not find plot tokens in one or both clearings")

        try:
            atomic_game_action(do_daylight_action)(player, "trick", plot1=p1, plot2=p2)
        except ValueError as e:
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
        origin = request.data["origin_clearing"]
        destination = int(request.data["clearing_number"])
        return self.generate_step(
            "move_count",
            "Select count of warriors to move.",
            "move-count",
            [{"type": "number", "name": "count"}],
            {"origin_clearing": origin, "destination_clearing": destination},
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
            atomic_game_action(do_daylight_action)(
                player, "move", origin=origin, destination=dest, count=count
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    # BATTLE
    def post_battle_clearing(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_number = int(request.data["clearing_number"])
        game = self.game(game_id)
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)

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
        clearing_number = request.data["clearing_number"]
        defender_faction = request.data["defender_faction"]
        game = self.game(game_id)
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)

        try:
            atomic_game_action(do_daylight_action)(
                player, "battle", defender_faction=defender_faction, clearing=clearing
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, CrowDaylight.CrowDaylightSteps.ACTIONS)
