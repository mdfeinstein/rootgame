from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from game.models.game_models import Clearing, Faction, Player
from game.models.moles.turn import MoleDaylight
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.moles.turn import validate_step
from game.queries.moles.daylight import (
    validate_card_in_hand,
    validate_build_clearing,
    validate_dig_clearing,
    validate_tunnel_source_clearing,
    get_actions_remaining,
)
from game.queries.general import (
    get_enemy_factions_in_clearing,
    validate_legal_move,
    validate_has_legal_moves,
    validate_enemy_pieces_in_clearing,
)
from game.transactions.moles.daylight.actions import (
    move,
    battle,
    recruit,
    build,
    dig,
    end_actions,
)
from game.decorators.transaction_decorator import atomic_game_action
from game.views.action_views.general import GameActionView, SubGameActionView


class MolesDaylightActionsView(GameActionView):
    action_name = "MOLES_DAYLIGHT_ACTIONS"
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "select_action",
        "prompt": "Select action or choose nothing to end daylight.",
        "endpoint": "select",
        "payload_details": [{"type": "action_type", "name": "action"}],
        "options": [
            {
                "value": "move",
                "label": "Move",
                "info": "Move warriors between adjacent clearings.",
            },
            {
                "value": "battle",
                "label": "Battle",
                "info": "Initiate combat in a clearing.",
            },
            {
                "value": "dig",
                "label": "Dig",
                "info": "Place or move a tunnel and move warriors.",
            },
            {
                "value": "recruit",
                "label": "Recruit",
                "info": "Recruit a warrior from supply to your burrow.",
            },
            {"value": "build", "label": "Build", "info": "Build a Citadel or Market."},
            {"value": "", "label": "Done", "info": "Finish daylight actions."},
        ],
    }

    def get(self, request):
        player = self.player(request, int(request.GET.get("game_id")))
        actions_left = get_actions_remaining(player)
        self.first_step = dict(self.first_step)
        self.first_step["prompt"] += f" ({actions_left} actions remaining)"
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "select":
                return self.post_select(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_select(self, request, game_id: int):
        from django.urls import reverse

        player = self.player(request, game_id)
        action = request.data.get("action", "")

        if action == "":
            atomic_game_action(end_actions)(player)
            return self.generate_completed_step()

        match action:
            case "move":
                return self.generate_redirect_step(reverse("moles-daylight-move"))
            case "battle":
                return self.generate_redirect_step(reverse("moles-daylight-battle"))
            case "dig":
                return self.generate_redirect_step(reverse("moles-daylight-dig"))
            case "recruit":
                return self.generate_redirect_step(reverse("moles-daylight-recruit"))
            case "build":
                return self.generate_redirect_step(reverse("moles-daylight-build"))
            case _:
                raise ValidationError("Invalid action")

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, MoleDaylight.MoleDaylightSteps.ACTIONS)


class MolesMoveView(SubGameActionView):
    subroute = "move"
    parent_view = MolesDaylightActionsView
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "move_origin",
        "prompt": "Select origin clearing.",
        "endpoint": "origin",
        "payload_details": [{"type": "clearing_number", "name": "clearing_number"}],
    }

    def get(self, request):
        player = self.player(request, int(request.GET.get("game_id")))
        actions_left = get_actions_remaining(player)
        self.first_step = dict(self.first_step)
        self.first_step["prompt"] = (
            f"Select origin clearing. ({actions_left} actions remaining)"
        )
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "origin":
                return self.post_origin(request, game_id)
            case "destination":
                return self.post_destination(request, game_id)
            case "count":
                return self.post_count(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_origin(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        clearing_number = int(request.data["clearing_number"])
        origin_clearing = Clearing.objects.get(
            game=game, clearing_number=clearing_number
        )

        validate_has_legal_moves(player, origin_clearing)

        return self.generate_step(
            "move_destination",
            "Select destination clearing.",
            "destination",
            [{"type": "clearing_number", "name": "clearing_number"}],
            {"origin_clearing": clearing_number},
        )

    def post_destination(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        origin_num = request.data["origin_clearing"]
        destination_num = int(request.data["clearing_number"])

        origin_clearing = Clearing.objects.get(game=game, clearing_number=origin_num)
        dest_clearing = Clearing.objects.get(game=game, clearing_number=destination_num)

        validate_legal_move(player, origin_clearing, dest_clearing)

        return self.generate_step(
            "move_count",
            "Select count of warriors to move.",
            "count",
            [{"type": "number", "name": "count"}],
            {"origin_clearing": origin_num, "destination_clearing": destination_num},
        )

    def post_count(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        origin_num = request.data["origin_clearing"]
        dest_num = request.data["destination_clearing"]
        count = int(request.data["count"])

        origin = Clearing.objects.get(game=game, clearing_number=origin_num)
        dest = Clearing.objects.get(game=game, clearing_number=dest_num)

        atomic_game_action(move)(player, origin, dest, count)
        return self.generate_completed_step()


class MolesBattleView(SubGameActionView):
    subroute = "battle"
    parent_view = MolesDaylightActionsView
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "battle_clearing",
        "prompt": "Select clearing to battle in.",
        "endpoint": "clearing",
        "payload_details": [{"type": "clearing_number", "name": "clearing_number"}],
    }

    def get(self, request):
        player = self.player(request, int(request.GET.get("game_id")))
        actions_left = get_actions_remaining(player)
        self.first_step = dict(
            self.first_step
        )  # copy dict to avoid mutating class attribute
        self.first_step["prompt"] = (
            f"Select clearing to battle in. ({actions_left} actions remaining)"
        )
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "clearing":
                return self.post_clearing(request, game_id)
            case "faction":
                return self.post_faction(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_clearing(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        clearing_number = int(request.data["clearing_number"])
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)

        enemy_players = validate_enemy_pieces_in_clearing(player, clearing)
        enemy_factions = [Faction(p.faction) for p in enemy_players]
        options = [
            {
                "value": f.value,
                "label": f.label,
                "info": f"Battle the {f.label}.",
            }
            for f in enemy_factions
        ]

        return self.generate_step(
            "battle_faction",
            "Select faction to battle.",
            "faction",
            [{"type": "faction", "name": "defender_faction"}],
            {"clearing_number": clearing_number},
            options=options,
        )

    def post_faction(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        clearing_number = request.data["clearing_number"]
        defender_faction = request.data["defender_faction"]
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)

        atomic_game_action(battle)(player, defender_faction, clearing)
        return self.generate_completed_step()


class MolesRecruitView(SubGameActionView):
    subroute = "recruit"
    parent_view = MolesDaylightActionsView
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "recruit_confirm",
        "prompt": "Recruit a warrior to your burrow.",
        "endpoint": "confirm",
        "payload_details": [{"type": "confirm", "name": "confirm"}],
        "options": [{"value": "true", "label": "Confirm", "info": "Build a Market."}],
    }

    def get(self, request):
        player = self.player(request, int(request.GET.get("game_id")))
        actions_left = get_actions_remaining(player)
        self.first_step = dict(self.first_step)
        self.first_step["prompt"] = (
            f"Recruit a warrior to your burrow. ({actions_left} actions remaining)"
        )
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "confirm":
                return self.post_confirm(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_confirm(self, request, game_id: int):
        player = self.player(request, game_id)
        atomic_game_action(recruit)(player)
        return self.generate_completed_step()


class MolesBuildView(SubGameActionView):
    subroute = "build"
    parent_view = MolesDaylightActionsView
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "build_type",
        "prompt": "Select building type.",
        "endpoint": "type",
        "payload_details": [{"type": "building_type", "name": "building_type"}],
        "options": [
            {"value": "citadel", "label": "Citadel", "info": "Build a Citadel."},
            {"value": "market", "label": "Market", "info": "Build a Market."},
        ],
    }

    def get(self, request):
        player = self.player(request, int(request.GET.get("game_id")))
        actions_left = get_actions_remaining(player)
        self.first_step = dict(self.first_step)
        self.first_step["prompt"] = (
            f"Select building type. ({actions_left} actions remaining)"
        )
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "type":
                return self.post_type(request, game_id)
            case "clearing":
                return self.post_clearing(request, game_id)
            case "card":
                return self.post_card(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_type(self, request, game_id: int):
        from game.queries.moles.daylight import get_available_building_from_supply

        player = self.player(request, game_id)
        building_type = request.data["building_type"]

        building_type_lower = building_type.lower()
        get_available_building_from_supply(player, building_type_lower)

        return self.generate_step(
            "build_clearing",
            "Select clearing to build in.",
            "clearing",
            [{"type": "clearing_number", "name": "clearing_number"}],
            {"building_type": building_type},
        )

    def post_clearing(self, request, game_id: int):
        from game.models.game_models import HandEntry

        player = self.player(request, game_id)
        game = self.game(game_id)
        building_type = request.data["building_type"]
        clearing_number = int(request.data["clearing_number"])

        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)

        return self.generate_step(
            "build_card",
            "Select card to use for building.",
            "card",
            [{"type": "card", "name": "card_name"}],
            {"building_type": building_type, "clearing_number": clearing_number},
        )

    def post_card(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        building_type = request.data["building_type"]
        clearing_number = request.data["clearing_number"]
        card_name = request.data["card_name"]

        card = CardsEP[card_name]
        validate_card_in_hand(player, card)

        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        validate_build_clearing(player, clearing, card)

        atomic_game_action(build)(player, card, building_type, clearing)
        return self.generate_completed_step()


class MolesDigView(SubGameActionView):
    subroute = "dig"
    parent_view = MolesDaylightActionsView
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "dig_clearing",
        "prompt": "Select clearing to dig in.",
        "endpoint": "clearing",
        "payload_details": [{"type": "clearing_number", "name": "clearing_number"}],
    }

    def get(self, request):
        player = self.player(request, int(request.GET.get("game_id")))
        actions_left = get_actions_remaining(player)
        self.first_step = dict(self.first_step)
        self.first_step["prompt"] = (
            f"Select clearing to dig in. ({actions_left} actions remaining)"
        )
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "clearing":
                return self.post_clearing(request, game_id)
            case "tunnel-source":
                return self.post_tunnel_source(request, game_id)
            case "card":
                return self.post_card(request, game_id)
            case "warrior-count":
                return self.post_warrior_count(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_clearing(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_number = int(request.data["clearing_number"])

        # Check if any tunnels exist in supply (need to move one)
        from game.models.moles.tokens import Tunnel

        tunnels_in_supply = Tunnel.objects.filter(
            player=player, clearing__isnull=True
        ).exists()

        if tunnels_in_supply:
            return self.generate_step(
                "dig_tunnel_source",
                "Select clearing with tunnel to move.",
                "tunnel-source",
                [{"type": "clearing_number", "name": "clearing_number"}],
                {"target_clearing": clearing_number},
            )
        else:
            return self.generate_step(
                "dig_card",
                "Select card to use for digging.",
                "card",
                [{"type": "card", "name": "card_name"}],
                {"target_clearing": clearing_number, "tunnel_source_clearing": None},
            )

    def post_tunnel_source(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        target_clearing_num = request.data["target_clearing"]
        tunnel_source_num = request.data.get("clearing_number")

        tunnel_source_clearing = None
        if tunnel_source_num is not None:
            tunnel_source_num = int(tunnel_source_num)
            tunnel_source = Clearing.objects.get(
                game=game, clearing_number=tunnel_source_num
            )
            validate_tunnel_source_clearing(player, tunnel_source)
            tunnel_source_clearing = tunnel_source_num

        return self.generate_step(
            "dig_card",
            "Select card to use for digging.",
            "card",
            [{"type": "card", "name": "card_name"}],
            {
                "target_clearing": target_clearing_num,
                "tunnel_source_clearing": tunnel_source_clearing,
            },
        )

    def post_card(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        card_name = request.data["card_name"]
        target_clearing_num = request.data["target_clearing"]
        tunnel_source_clearing_num = request.data.get("tunnel_source_clearing")

        card = CardsEP[card_name]
        validate_card_in_hand(player, card)

        target_clearing = Clearing.objects.get(
            game=game, clearing_number=target_clearing_num
        )
        validate_dig_clearing(player, target_clearing, card)

        return self.generate_step(
            "dig_warrior_count",
            "Select number of warriors to move (0-4).",
            "warrior-count",
            [{"type": "number", "name": "count"}],
            {
                "card_name": card_name,
                "target_clearing": target_clearing_num,
                "tunnel_source_clearing": tunnel_source_clearing_num,
            },
        )

    def post_warrior_count(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        card_name = request.data["card_name"]
        target_clearing_num = request.data["target_clearing"]
        tunnel_source_clearing_num = request.data.get("tunnel_source_clearing")
        count = int(request.data["count"])

        target_clearing = Clearing.objects.get(
            game=game, clearing_number=target_clearing_num
        )
        tunnel_source_clearing = None
        if tunnel_source_clearing_num is not None:
            tunnel_source_clearing = Clearing.objects.get(
                game=game, clearing_number=tunnel_source_clearing_num
            )

        atomic_game_action(dig)(
            player,
            card_name,
            target_clearing,
            count,
            clearing_to_move_tunnel_from=tunnel_source_clearing,
        )
        return self.generate_completed_step()
