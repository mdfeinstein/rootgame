from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from game.models.game_models import Clearing, Faction, Player, HandEntry
from game.models.moles.turn import MoleDaylight
from game.models.moles.ministers import Minister
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.moles.turn import validate_step, get_phase
from game.queries.moles.daylight import (
    get_available_ministers,
    get_copyable_ministers_for_mayor,
    validate_build_clearing,
    validate_foremole_clearing,
    validate_banker_cards,
    validate_minister_unused,
    validate_brigadier_action,
    validate_no_brigadier_in_progress,
    validate_minister_is_swayed,
)
from game.queries.general import (
    get_enemy_factions_in_clearing,
    validate_legal_move,
    validate_has_legal_moves,
    validate_enemy_pieces_in_clearing,
    validate_player_has_card_in_hand,
)
from game.transactions.moles.daylight.minister_actions import (
    use_marshal,
    use_captain,
    use_foremole,
    use_brigadier,
    use_banker,
    use_duchess,
    use_earl,
    use_baron,
    use_mayor,
    end_minister_actions,
    skip_brigadier,
)
from game.decorators.transaction_decorator import atomic_game_action
from game.views.action_views.general import GameActionView, SubGameActionView


class MolesMinisterActionsView(GameActionView):
    action_name = "MOLES_MINISTER_ACTIONS"
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "select_minister",
        "prompt": "Select a minister to use or choose nothing to end.",
        "endpoint": "select",
        "payload_details": [{"type": "action", "name": "action"}],
        "options": [],
    }

    def get(self, request):
        player = self.player(request, int(request.GET.get("game_id")))
        phase = get_phase(player)

        self.first_step = dict(self.first_step)

        # Brigadier mid-sequence: only brigadier or skip allowed
        if phase.brigadier_action != MoleDaylight.BrigadierAction.NONE:
            action_type = "battling" if phase.brigadier_action == MoleDaylight.BrigadierAction.BATTLE else "moving"
            self.first_step["prompt"] = f"Continue Brigadier {action_type} or end."
            self.first_step["options"] = [
                {
                    "value": "brigadier",
                    "label": f"Brigadier: second {action_type}",
                    "info": f"Use Brigadier's second {action_type} action.",
                },
                {
                    "value": "skip_brigadier",
                    "label": f"End Brigadier {action_type}",
                    "info": "End Brigadier's effects.",
                },
                {"value": "", "label": "Done", "info": "Finish minister actions."},
            ]
        else:
            # Normal case: show all available ministers and Mayor
            available_ministers = get_available_ministers(player)
            options = []
            for minister in available_ministers:
                minister_labels = {
                    Minister.MinisterName.MARSHAL: (
                        "Marshal",
                        "Move warriors between clearings.",
                    ),
                    Minister.MinisterName.CAPTAIN: ("Captain", "Initiate combat."),
                    Minister.MinisterName.FOREMOLE: (
                        "Foremole",
                        "Build without suit restriction.",
                    ),
                    Minister.MinisterName.BRIGADIER: (
                        "Brigadier",
                        "Move or battle (up to twice).",
                    ),
                    Minister.MinisterName.BANKER: (
                        "Banker",
                        "Select cards for points.",
                    ),
                    Minister.MinisterName.DUCHESS_OF_MUD: (
                        "Duchess of Mud",
                        "Gain points if all tunnels on map.",
                    ),
                    Minister.MinisterName.EARL_OF_STONE: (
                        "Earl of Stone",
                        "Gain points from citadels.",
                    ),
                    Minister.MinisterName.BARON_OF_DIRT: (
                        "Baron of Dirt",
                        "Gain points from markets.",
                    ),
                }
                label, info = minister_labels.get(
                    minister.name, (minister.name.replace("_", " ").title(), "")
                )
                options.append(
                    {
                        "value": minister.name,
                        "label": label,
                        "info": info,
                    }
                )
            # Check if Mayor is swayed and unused
            try:
                validate_minister_unused(player, Minister.MinisterName.MAYOR)
                options.append(
                    {
                        "value": "mayor",
                        "label": "Mayor",
                        "info": "Copy any swayed minister's action.",
                    }
                )
            except (ValidationError, Exception):
                pass
            options.append(
                {"value": "", "label": "Done", "info": "Finish minister actions."}
            )
            self.first_step["options"] = options

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
        phase = get_phase(player)
        action = request.data.get("action", "")

        # API request rejection: if brigadier mid-action, only brigadier/skip allowed
        if phase.brigadier_action != MoleDaylight.BrigadierAction.NONE:
            if action not in ("", "brigadier", "skip_brigadier"):
                raise ValidationError(
                    "Cannot use another minister while Brigadier action is in progress."
                )

        if action == "":
            atomic_game_action(end_minister_actions)(player)
            return self.generate_completed_step()

        if action == "skip_brigadier":
            atomic_game_action(skip_brigadier)(player)
            return self.generate_completed_step()

        match action:
            case "marshal":
                return self.generate_redirect_step(reverse("moles-minister-marshal"))
            case "captain":
                return self.generate_redirect_step(reverse("moles-minister-captain"))
            case "foremole":
                return self.generate_redirect_step(reverse("moles-minister-foremole"))
            case "brigadier":
                return self.generate_redirect_step(reverse("moles-minister-brigadier"))
            case "banker":
                return self.generate_redirect_step(reverse("moles-minister-banker"))
            case "duchess":
                atomic_game_action(use_duchess)(player)
                return self.generate_completed_step()
            case "earl":
                atomic_game_action(use_earl)(player)
                return self.generate_completed_step()
            case "baron":
                atomic_game_action(use_baron)(player)
                return self.generate_completed_step()
            case "mayor":
                return self.generate_redirect_step(reverse("moles-minister-mayor"))
            case _:
                raise ValidationError("Invalid minister")

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)


# ============================================================================
# SUB-VIEWS FOR EACH MINISTER
# ============================================================================


class MolesMinisterMayorView(GameActionView):
    action_name = "MOLES_MINISTER_MAYOR"
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "select_minister_to_copy",
        "prompt": "Select a swayed minister to copy.",
        "endpoint": "select",
        "payload_details": [{"type": "action", "name": "action"}],
        "options": [],
    }

    def get(self, request):
        player = self.player(request, int(request.GET.get("game_id")))

        self.first_step = dict(self.first_step)

        # Get all swayed ministers that Mayor can copy
        copyable_ministers = get_copyable_ministers_for_mayor(player)

        if not copyable_ministers:
            self.first_step["prompt"] = "No swayed ministers available to copy."
            self.first_step["options"] = [
                {"value": "", "label": "Done", "info": "Finish minister actions."}
            ]
        else:
            options = []
            for minister in copyable_ministers:
                minister_labels = {
                    Minister.MinisterName.MARSHAL: ("Marshal", "Copy Marshal (move)."),
                    Minister.MinisterName.CAPTAIN: (
                        "Captain",
                        "Copy Captain (battle).",
                    ),
                    Minister.MinisterName.FOREMOLE: (
                        "Foremole",
                        "Copy Foremole (build).",
                    ),
                    Minister.MinisterName.BRIGADIER: (
                        "Brigadier",
                        "Copy Brigadier (move or battle).",
                    ),
                    Minister.MinisterName.BANKER: ("Banker", "Copy Banker (cards)."),
                }
                label, info = minister_labels.get(
                    minister.name, (minister.name.replace("_", " ").title(), "")
                )
                options.append(
                    {
                        "value": minister.name,
                        "label": label,
                        "info": info,
                    }
                )
            options.append(
                {"value": "", "label": "Done", "info": "Finish minister actions."}
            )
            self.first_step["options"] = options

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
            atomic_game_action(end_minister_actions)(player)
            return self.generate_completed_step()

        # Convert string to MinisterName enum
        try:
            minister_name = Minister.MinisterName(action)
        except ValueError:
            raise ValidationError("Invalid minister")

        # Mayor cannot copy lords (Duchess, Earl, Baron)
        lords = {
            Minister.MinisterName.DUCHESS_OF_MUD,
            Minister.MinisterName.EARL_OF_STONE,
            Minister.MinisterName.BARON_OF_DIRT,
        }
        if minister_name in lords:
            raise ValidationError("Mayor cannot copy lords")

        # Validate that the selected minister is swayed
        try:
            validate_minister_is_swayed(player, minister_name)
        except Exception as e:
            raise ValidationError(str(e))

        # Route to the appropriate minister view with is_mayor=true
        minister_routes = {
            Minister.MinisterName.MARSHAL: "moles-minister-marshal",
            Minister.MinisterName.CAPTAIN: "moles-minister-captain",
            Minister.MinisterName.FOREMOLE: "moles-minister-foremole",
            Minister.MinisterName.BRIGADIER: "moles-minister-brigadier",
            Minister.MinisterName.BANKER: "moles-minister-banker",
            Minister.MinisterName.DUCHESS_OF_MUD: "moles-minister-duchess",
            Minister.MinisterName.EARL_OF_STONE: "moles-minister-earl",
            Minister.MinisterName.BARON_OF_DIRT: "moles-minister-baron",
        }

        route_name = minister_routes.get(minister_name)
        if route_name is None:
            raise ValidationError("Invalid minister")

        redirect_url = reverse(route_name) + f"?is_mayor=true"
        return self.generate_redirect_step(redirect_url)

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)


class MolesMinisterMarshalView(SubGameActionView):
    subroute = "marshal"
    parent_view = MolesMinisterActionsView
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "marshal_origin",
        "prompt": "Select origin clearing.",
        "endpoint": "origin",
        "payload_details": [{"type": "clearing_number", "name": "clearing_number"}],
    }

    def get(self, request):
        is_mayor = request.GET.get("is_mayor") == "true"
        self.first_step = dict(self.first_step)
        if is_mayor:
            self.first_step["accumulated_payload"] = {"is_mayor": True}
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

        accumulated = {"origin_clearing": clearing_number}
        if request.data.get("is_mayor"):
            accumulated["is_mayor"] = True

        return self.generate_step(
            "marshal_destination",
            "Select destination clearing.",
            "destination",
            [{"type": "clearing_number", "name": "clearing_number"}],
            accumulated,
        )

    def post_destination(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        origin_num = request.data["origin_clearing"]
        destination_num = int(request.data["clearing_number"])

        origin_clearing = Clearing.objects.get(game=game, clearing_number=origin_num)
        dest_clearing = Clearing.objects.get(game=game, clearing_number=destination_num)

        validate_legal_move(player, origin_clearing, dest_clearing)

        accumulated = {
            "origin_clearing": origin_num,
            "destination_clearing": destination_num,
        }
        if request.data.get("is_mayor"):
            accumulated["is_mayor"] = True

        return self.generate_step(
            "marshal_count",
            "Select count of warriors to move.",
            "count",
            [{"type": "number", "name": "count"}],
            accumulated,
        )

    def post_count(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        origin_num = request.data["origin_clearing"]
        dest_num = request.data["destination_clearing"]
        count = int(request.data["count"])
        is_mayor = request.data.get("is_mayor", False)

        origin = Clearing.objects.get(game=game, clearing_number=origin_num)
        dest = Clearing.objects.get(game=game, clearing_number=dest_num)

        if is_mayor:
            atomic_game_action(use_mayor)(
                player, Minister.MinisterName.MARSHAL, origin, dest, count
            )
        else:
            atomic_game_action(use_marshal)(player, origin, dest, count)
        return self.generate_completed_step()


class MolesMinisterCaptainView(SubGameActionView):
    subroute = "captain"
    parent_view = MolesMinisterActionsView
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "captain_clearing",
        "prompt": "Select clearing to battle in.",
        "endpoint": "clearing",
        "payload_details": [{"type": "clearing_number", "name": "clearing_number"}],
    }

    def get(self, request):
        is_mayor = request.GET.get("is_mayor") == "true"
        self.first_step = dict(self.first_step)
        if is_mayor:
            self.first_step["accumulated_payload"] = {"is_mayor": True}
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

        accumulated = {"clearing_number": clearing_number}
        if request.data.get("is_mayor"):
            accumulated["is_mayor"] = True

        return self.generate_step(
            "captain_faction",
            "Select faction to battle.",
            "faction",
            [{"type": "faction", "name": "defender_faction"}],
            accumulated,
            options=options,
        )

    def post_faction(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        clearing_number = request.data["clearing_number"]
        defender_faction_str = request.data["defender_faction"]
        defender_faction = (
            Faction(defender_faction_str)
            if isinstance(defender_faction_str, str)
            else defender_faction_str
        )
        is_mayor = request.data.get("is_mayor", False)
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)

        if is_mayor:
            atomic_game_action(use_mayor)(
                player, Minister.MinisterName.CAPTAIN, defender_faction, clearing
            )
        else:
            atomic_game_action(use_captain)(player, defender_faction, clearing)
        return self.generate_completed_step()


class MolesMinisterForemoleView(SubGameActionView):
    subroute = "foremole"
    parent_view = MolesMinisterActionsView
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "foremole_type",
        "prompt": "Select building type.",
        "endpoint": "type",
        "payload_details": [{"type": "building_type", "name": "building_type"}],
        "options": [
            {"value": "Citadel", "label": "Citadel", "info": "Build a Citadel."},
            {"value": "Market", "label": "Market", "info": "Build a Market."},
        ],
    }

    def get(self, request):
        is_mayor = request.GET.get("is_mayor") == "true"
        self.first_step = dict(self.first_step)
        if is_mayor:
            self.first_step["accumulated_payload"] = {"is_mayor": True}
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

        accumulated = {"building_type": building_type}
        if request.data.get("is_mayor"):
            accumulated["is_mayor"] = True

        return self.generate_step(
            "foremole_clearing",
            "Select clearing to build in.",
            "clearing",
            [{"type": "clearing_number", "name": "clearing_number"}],
            accumulated,
        )

    def post_clearing(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        building_type = request.data["building_type"]
        clearing_number = int(request.data["clearing_number"])

        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        validate_foremole_clearing(player, clearing)

        accumulated = {
            "building_type": building_type,
            "clearing_number": clearing_number,
        }
        if request.data.get("is_mayor"):
            accumulated["is_mayor"] = True

        return self.generate_step(
            "foremole_card",
            "Select card to use for building.",
            "card",
            [{"type": "card", "name": "card_name"}],
            accumulated,
        )

    def post_card(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        building_type = request.data["building_type"]
        clearing_number = request.data["clearing_number"]
        card_name = request.data["card_name"]
        is_mayor = request.data.get("is_mayor", False)

        card = CardsEP[card_name]
        validate_player_has_card_in_hand(player, card)

        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        validate_foremole_clearing(player, clearing)

        if is_mayor:
            atomic_game_action(use_mayor)(
                player,
                Minister.MinisterName.FOREMOLE,
                card,
                clearing,
                building_type.lower(),
            )
        else:
            atomic_game_action(use_foremole)(
                player, card, clearing, building_type.lower()
            )
        return self.generate_completed_step()


class MolesMinisterBrigadierView(SubGameActionView):
    subroute = "brigadier"
    parent_view = MolesMinisterActionsView
    faction = Faction.MOLES

    def get(self, request):
        player = self.player(request, int(request.GET.get("game_id")))
        phase = get_phase(player)
        is_mayor = request.GET.get("is_mayor") == "true"

        # Determine which endpoint to start at based on brigadier_action
        if phase.brigadier_action == MoleDaylight.BrigadierAction.NONE:
            self.first_step = {
                "faction": Faction.MOLES.label,
                "name": "brigadier_action_type",
                "prompt": "Select action type.",
                "endpoint": "action-type",
                "payload_details": [{"type": "action_type", "name": "action_type"}],
                "options": [
                    {"value": "move", "label": "Move", "info": "Move warriors."},
                    {"value": "battle", "label": "Battle", "info": "Initiate combat."},
                ],
            }
        elif phase.brigadier_action == MoleDaylight.BrigadierAction.BATTLE:
            self.first_step = {
                "faction": Faction.MOLES.label,
                "name": "brigadier_clearing",
                "prompt": "Select clearing to battle in.",
                "endpoint": "clearing",
                "payload_details": [
                    {"type": "clearing_number", "name": "clearing_number"}
                ],
            }
        else:  # MOVE
            self.first_step = {
                "faction": Faction.MOLES.label,
                "name": "brigadier_origin",
                "prompt": "Select origin clearing.",
                "endpoint": "origin",
                "payload_details": [
                    {"type": "clearing_number", "name": "clearing_number"}
                ],
            }

        if is_mayor:
            self.first_step = dict(self.first_step)
            self.first_step["accumulated_payload"] = {"is_mayor": True}

        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "action-type":
                return self.post_action_type(request, game_id)
            case "origin":
                return self.post_origin(request, game_id)
            case "destination":
                return self.post_destination(request, game_id)
            case "count":
                return self.post_count(request, game_id)
            case "clearing":
                return self.post_clearing(request, game_id)
            case "faction":
                return self.post_faction(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_action_type(self, request, game_id: int):
        action_type = request.data.get("action_type", "")

        accumulated = {"action_type": action_type}
        if request.data.get("is_mayor"):
            accumulated["is_mayor"] = True

        if action_type == "move":
            return self.generate_step(
                "brigadier_origin",
                "Select origin clearing.",
                "origin",
                [{"type": "clearing_number", "name": "clearing_number"}],
                accumulated,
            )
        elif action_type == "battle":
            return self.generate_step(
                "brigadier_clearing",
                "Select clearing to battle in.",
                "clearing",
                [{"type": "clearing_number", "name": "clearing_number"}],
                accumulated,
            )
        else:
            raise ValidationError("Invalid action type")

    def post_origin(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        clearing_number = int(request.data["clearing_number"])
        origin_clearing = Clearing.objects.get(
            game=game, clearing_number=clearing_number
        )

        validate_has_legal_moves(player, origin_clearing)

        accumulated = {"action_type": "move", "origin_clearing": clearing_number}
        if request.data.get("is_mayor"):
            accumulated["is_mayor"] = True

        return self.generate_step(
            "brigadier_destination",
            "Select destination clearing.",
            "destination",
            [{"type": "clearing_number", "name": "clearing_number"}],
            accumulated,
        )

    def post_destination(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        origin_num = request.data["origin_clearing"]
        destination_num = int(request.data["clearing_number"])

        origin_clearing = Clearing.objects.get(game=game, clearing_number=origin_num)
        dest_clearing = Clearing.objects.get(game=game, clearing_number=destination_num)

        validate_legal_move(player, origin_clearing, dest_clearing)

        accumulated = {
            "action_type": "move",
            "origin_clearing": origin_num,
            "destination_clearing": destination_num,
        }
        if request.data.get("is_mayor"):
            accumulated["is_mayor"] = True

        return self.generate_step(
            "brigadier_count",
            "Select count of warriors to move.",
            "count",
            [{"type": "number", "name": "count"}],
            accumulated,
        )

    def post_count(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        origin_num = request.data["origin_clearing"]
        dest_num = request.data["destination_clearing"]
        count = int(request.data["count"])
        is_mayor = request.data.get("is_mayor", False)

        origin = Clearing.objects.get(game=game, clearing_number=origin_num)
        dest = Clearing.objects.get(game=game, clearing_number=dest_num)

        if is_mayor:
            atomic_game_action(use_mayor)(
                player, Minister.MinisterName.BRIGADIER, "move", origin, dest, count
            )
        else:
            atomic_game_action(use_brigadier)(player, "move", origin, dest, count)
        return self.generate_completed_step()

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

        accumulated = {"action_type": "battle", "clearing_number": clearing_number}
        if request.data.get("is_mayor"):
            accumulated["is_mayor"] = True

        return self.generate_step(
            "brigadier_faction",
            "Select faction to battle.",
            "faction",
            [{"type": "faction", "name": "defender_faction"}],
            accumulated,
            options=options,
        )

    def post_faction(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        clearing_number = request.data["clearing_number"]
        defender_faction_str = request.data["defender_faction"]
        defender_faction = (
            Faction(defender_faction_str)
            if isinstance(defender_faction_str, str)
            else defender_faction_str
        )
        is_mayor = request.data.get("is_mayor", False)
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)

        if is_mayor:
            atomic_game_action(use_mayor)(
                player,
                Minister.MinisterName.BRIGADIER,
                "battle",
                defender_faction,
                clearing,
            )
        else:
            atomic_game_action(use_brigadier)(
                player, "battle", defender_faction, clearing
            )
        return self.generate_completed_step()


class MolesMinisterBankerView(SubGameActionView):
    subroute = "banker"
    parent_view = MolesMinisterActionsView
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "banker_select_card",
        "prompt": "Select a card or choose Done to submit.",
        "endpoint": "card",
        "payload_details": [{"type": "card", "name": "card_name"}],
    }

    def get(self, request):
        is_mayor = request.GET.get("is_mayor") == "true"
        self.first_step = dict(self.first_step)
        self.first_step["prompt"] = (
            "Select a card or choose Done to submit. (0 cards selected)"
        )
        if is_mayor:
            self.first_step["accumulated_payload"] = {"is_mayor": True}
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "card":
                return self.post_card(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_card(self, request, game_id: int):
        player = self.player(request, game_id)
        card_name = request.data.get("card_name", "")
        # accumulated_payload is flattened into request.data by the test client
        accumulated = request.data.get("selected_cards", [])
        is_mayor = request.data.get("is_mayor", False)

        # If empty string, player is done
        if card_name == "":
            if not accumulated:
                raise ValidationError("Must select at least one card")
            cards = [CardsEP[name] for name in accumulated]
            if is_mayor:
                atomic_game_action(use_mayor)(
                    player, Minister.MinisterName.BANKER, cards
                )
            else:
                atomic_game_action(use_banker)(player, cards)
            return self.generate_completed_step()

        # Add card to accumulated list
        card = CardsEP[card_name]
        validate_player_has_card_in_hand(player, card)

        # Validate suit matching
        new_list = accumulated + [card_name]
        cards_to_validate = [CardsEP[name] for name in new_list]
        validate_banker_cards(player, cards_to_validate)

        # Generate options for next card selection
        hand_entries = HandEntry.objects.filter(player=player)
        hand_cards = [CardsEP[he.card.card_type] for he in hand_entries]

        # Filter by suit matching
        suits = [CardsEP[name].value.suit for name in accumulated]
        unique_suits = set(s for s in suits if s != "Wild")

        options = []
        for card_option in hand_cards:
            # Check if suit matches
            card_suit = card_option.value.suit
            if unique_suits and card_suit != "Wild" and card_suit not in unique_suits:
                continue
            options.append(
                {
                    "value": card_option.name,
                    "label": card_option.value.title,
                }
            )

        # Add Done option
        options.append({"value": "", "label": "Done"})

        accumulated_payload = {"selected_cards": new_list}
        if is_mayor:
            accumulated_payload["is_mayor"] = True

        return self.generate_step(
            "banker_select_card",
            f"Select a card or choose Done to submit. ({len(new_list)} cards selected)",
            "card",
            [{"type": "card", "name": "card_name"}],
            accumulated_payload,
            options=options,
        )


