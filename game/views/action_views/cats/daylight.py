from game.game_data.cards.exiles_and_partisans import CardsEP
from game.game_data.general.game_enums import Suit
from game.models.cats.buildings import CatBuildingTypes, Workshop
from game.models.cats.tokens import CatWood
from game.models.cats.turn import CatDaylight
from game.models.game_models import (
    Card,
    Clearing,
    Faction,
    Game,
    HandEntry,
    Piece,
    Player,
    Warrior,
)
from game.queries.cats.building import get_usable_wood_for_building, get_wood_cost
from game.queries.cats.crafting import (
    get_all_unused_workshops,
    get_unused_workshop_by_clearing_number,
    validate_crafting_pieces_satisfy_requirements,
    validate_unused_workshops_by_clearing_number,
)
from game.queries.cats.recruit import (
    is_enough_reserve,
    is_recruit_used,
    troops_in_reserve,
    unused_recruiters,
)
from game.queries.cats.turn import get_actions_remaining, get_phase
from game.queries.cats.wood import get_sawmills_by_suit
from game.queries.general import (
    determine_clearing_rule,
    get_current_player,
    validate_player_has_card_in_hand,
    player_has_pieces_in_clearing,
    player_has_warriors_in_clearing,
)
from game.serializers.general_serializers import GameActionStepSerializer
from game.transactions.battle import start_battle
from game.transactions.cats import (
    action_used,
    birds_for_hire,
    build_building,
    cat_battle,
    cat_build,
    cat_craft_card,
    cat_march,
    cat_recruit,
    cat_recruit_all,
    end_action_step,
    end_crafting_step,
    overwork,
)
from game.decorators.transaction_decorator import atomic_game_action
from game.transactions.general import craft_card, move_warriors
from game.utility.textchoice import get_choice_value_by_label_or_value, next_choice
from game.views.action_views.general import GameActionView
from rest_framework.views import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status

from django.db import transaction


class CatCraftStepView(GameActionView):
    action_name = "CAT_CRAFT_STEP"
    faction_string = Faction.CATS.label
    faction = Faction.CATS

    first_step = {
        "faction": faction_string,
        "name": "select_card",
        "prompt": "Select card to craft or choose nothing to end crafting step.",
        "endpoint": "card",
        "payload_details": [{"type": "card", "name": "card_to_craft"}],
        "options": [
            {"value": "", "label": "Done Crafting"},
        ],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "card":
            return self.post_card(request, game_id)
        elif route == "piece":
            return self.post_piece(request, game_id)

        return Response({"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST)

    def post_card(self, request, game_id: int):
        if request.data["card_to_craft"] == "":
            try:
                atomic_game_action(end_crafting_step)(self.player(request, game_id))
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return Response({"name": "completed"})
        self.validate(request, game_id)
        card_type = CardsEP[request.data["card_to_craft"]]
        suits_needed = [suit.label for suit in card_type.value.cost]
        workshop_count = get_all_unused_workshops(self.player(request, game_id)).count()
        print(f"workshop count: {workshop_count}")
        print(f"suits needed: {suits_needed}")
        if workshop_count < len(suits_needed):
            raise ValidationError(
                f"Not enough unused workshops to craft this card. ({workshop_count} unused workshops remaining)"
            )
        serializer = GameActionStepSerializer(
            {
                "faction": self.faction_string,
                "name": "select_piece",
                "prompt": "Select a crafting piece to craft with. "
                + f"Needed: {suits_needed}",
                "endpoint": "piece",
                "payload_details": [
                    {"type": "clearing_number", "name": "cn_0"},
                ],
                "accumulated_payload": {
                    "card_to_craft": request.data["card_to_craft"],
                },
            }
        )
        return Response(serializer.data)

    def post_piece(self, request, game_id: int):
        try:
            satisfied, crafting_pieces = self.validate(request, game_id)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # check if we have enough pieces. if so, go to confirm. if not, go to piece
        accumulated_payload = {"card_to_craft": request.data["card_to_craft"]}
        cn_count = 0
        for key, value in request.data.items():
            if "cn_" in key:
                accumulated_payload[key] = value
                cn_count += 1

        if not satisfied:  # need to select more crafting pieces
            card_type = CardsEP[request.data["card_to_craft"]]
            suits_needed = [suit.label for suit in card_type.value.cost]
            suits_selected = [
                Suit(workshop.building_slot.clearing.suit).label
                for workshop in crafting_pieces
            ]
            step = {
                "faction": self.faction_string,
                "name": "select_piece",
                "prompt": "Select a crafting piece to craft with ."
                + f"Needed: {suits_needed}. Selected: {suits_selected}",
                "endpoint": "piece",
                "payload_details": [
                    {"type": "clearing_number", "name": f"cn_{cn_count}"},
                ],
                "accumulated_payload": accumulated_payload,
            }
        else:  # we have all we need
            satisfied, crafting_pieces = self.validate(request, game_id)
            # craft
            card_type = CardsEP[request.data["card_to_craft"].upper()]
            if not satisfied:
                raise ValidationError("Not enough crafting pieces to craft card")
            try:
                atomic_game_action(cat_craft_card)(
                    self.player(request, game_id), card_type, crafting_pieces
                )
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def validate(self, request, game_id: int) -> tuple[bool, list[Workshop]]:

        # validate card in hand and return card info
        card = self.validate_card(request, game_id)
        # get crafting pieces (or determine if not possible)
        satisfied, crafting_pieces = self.validate_crafting_pieces(
            request, game_id, card
        )
        return satisfied, crafting_pieces

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        phase = get_phase(self.player(request, game_id))
        if type(phase) != CatDaylight:
            raise ValidationError("Not Daylight phase")
        if phase.step != CatDaylight.CatDaylightSteps.CRAFTING:
            raise ValidationError(
                "Wrong Step, not Crafting Step. Current step: {phase.step.value}"
            )

    def validate_card(self, request, game_id: int) -> CardsEP:
        """raises if card is not in players hand or is not craftable"""
        card_info = request.data["card_to_craft"]
        card = CardsEP[card_info]
        validate_player_has_card_in_hand(self.player(request, game_id), card)
        # check that card is craftable
        card_details = card.value
        if card_details.craftable is False:
            raise ValidationError("Card is not craftable")
        return CardsEP[card_info]

    def validate_crafting_pieces(
        self, request, game_id: int, card: CardsEP
    ) -> tuple[bool, list[Workshop]]:
        """returns a tuple of (crafting_satisfied, list of crafting pieces)
        the first item can be used to confirm that we have enough crafting pieces to craft the card
        """
        crafting_piece_clearing_numbers: dict[int, int] = (
            {}
        )  # clearing_number: piece_count
        for key, value in request.data.items():
            if "cn_" in key:
                try:
                    crafting_piece_clearing_numbers[value] += 1
                except KeyError:
                    crafting_piece_clearing_numbers[value] = 1
        game = self.game(game_id)
        player = self.player(request, game_id)
        # check that we have workshops in the given clearing numbers
        crafting_pieces: list[Workshop] = []
        for clearing_number in crafting_piece_clearing_numbers:
            try:
                workshops = validate_unused_workshops_by_clearing_number(
                    player,
                    clearing_number,
                    crafting_piece_clearing_numbers[clearing_number],
                )
                crafting_pieces.extend(workshops)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})

        satisfied = validate_crafting_pieces_satisfy_requirements(
            player, card, crafting_pieces
        )
        return satisfied, crafting_pieces

    def end_step(self, request, game_id: int):
        player = self.player(request, game_id)
        end_crafting_step(player)


class CatActionsView(GameActionView):
    action_name = "CAT_ACTIONS"
    faction_string = Faction.CATS.label
    faction = Faction.CATS

    first_step = {
        "faction": faction_string,
        "name": "select_action",
        "prompt": "Select action: march, battle, build, overwork, or birds-for-hire. Or, choose nothing to end action step.",
        "endpoint": "action",
        "payload_details": [{"type": "action_type", "name": "action"}],
        "options": [
            {"value": "march", "label": "March"},
            {"value": "battle", "label": "Battle"},
            {"value": "build", "label": "Build"},
            {"value": "recruit", "label": "Recruit"},
            {"value": "overwork", "label": "Overwork"},
            {"value": "birds-for-hire", "label": "Birds For Hire"},
            {"value": "", "label": "Done"},
        ],
    }

    def get(self, request):
        # if midmarch, return the step as the second march move. otherwise, return the first_step as declared above
        game_id = int(request.query_params.get("game_id"))
        daylight = get_phase(self.player(request, game_id))
        if type(daylight) != CatDaylight:
            raise ValidationError("Not Daylight phase")
        if daylight.midmarch:
            step = {
                "faction": self.faction_string,
                "name": "select_move_clearing_origin",
                "prompt": "Select a clearing to move from for second move of march.",
                "endpoint": "march-clearing-origin",
                "payload_details": [
                    {"type": "clearing_number", "name": "origin_clearing_number"}
                ],
            }
        else:
            step = {
                "faction": self.faction_string,
                "name": "select_action",
                "prompt": "Select action."
                + f" Actions remaining: {daylight.actions_left}",
                "endpoint": "action",
                "payload_details": [{"type": "action_type", "name": "action"}],
                "options": [
                    {"value": "march", "label": "March"},
                    {"value": "battle", "label": "Battle"},
                    {"value": "build", "label": "Build"},
                    {"value": "recruit", "label": "Recruit"},
                    {"value": "overwork", "label": "Overwork"},
                    {"value": "birds-for-hire", "label": "Birds For Hire"},
                    {"value": "", "label": "Done"},
                ],
            }
        self.first_step = step
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "action":
                return self.post_action(request, game_id)
            case "march-clearing-origin":
                return self.post_march_clearing_origin(request, game_id)
            case "march-clearing-destination":
                return self.post_march_clearing_destination(request, game_id)
            case "march-count":
                return self.post_march_count(request, game_id)
            case "battle-clearing":
                return self.post_battle_clearing(request, game_id)
            case "battle-defender":
                return self.post_battle_defender(request, game_id)
            case "build-building":
                return self.post_build_building(request, game_id)
            case "build-clearing":
                return self.post_build_clearing(request, game_id)
            case "build-wood":
                return self.post_build_wood(request, game_id)
            case "overwork-card":
                return self.post_overwork_card(request, game_id)
            case "overwork-clearing":
                return self.post_overwork_clearing(request, game_id)
            case "recruit-all":
                return self.post_recruit_all(request, game_id)
            case "recruit-clearing":
                return self.post_recruit_clearing(request, game_id)
            case "birdsforhire-card":
                return self.post_birdsforhire_card(request, game_id)
            case _:
                return Response(
                    {"detail": "Invalid route"}, status=status.HTTP_404_NOT_FOUND
                )

    def post_action(self, request, game_id: int):
        if request.data["action"] == "":
            try:
                atomic_game_action(end_action_step)(self.player(request, game_id))
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        actions_remaining = get_actions_remaining(self.player(request, game_id))
        if actions_remaining == 0 and request.data["action"] != "birds-for-hire":
            raise ValidationError("No actions remaining")
        match request.data["action"]:
            case "march":
                step = {
                    "faction": self.faction_string,
                    "name": "select_move_clearing_origin",
                    "prompt": "Select a clearing to move from for first move of march.",
                    "endpoint": "march-clearing-origin",
                    "payload_details": [
                        {"type": "clearing_number", "name": "origin_clearing_number"}
                    ],
                }
                pass
            case "battle":
                step = {
                    "faction": self.faction_string,
                    "name": "select_clearing",
                    "prompt": "Select a clearing to battle in",
                    "endpoint": "battle-clearing",
                    "payload_details": [
                        {"type": "clearing_number", "name": "battle_clearing_number"}
                    ],
                }
            case "build":
                step = {
                    "faction": self.faction_string,
                    "name": "select_build_building",
                    "prompt": "Select a building to build",
                    "endpoint": "build-building",
                    "payload_details": [
                        {"type": "building_type", "name": "building_type"}
                    ],
                    "options": [
                        {"value": "sawmill", "label": "Sawmill"},
                        {"value": "workshop", "label": "Workshop"},
                        {"value": "recruiter", "label": "Recruiter"},
                    ],
                }
            case "overwork":
                step = {
                    "faction": self.faction_string,
                    "name": "select_overwork_card",
                    "prompt": "Select a card to overwork",
                    "endpoint": "overwork-card",
                    "payload_details": [{"type": "card", "name": "overwork_card"}],
                }
            case "recruit":
                if is_recruit_used(self.player(request, game_id)):
                    raise ValidationError("Recruit has already been used this turn")
                # if more reserve warriors than recruiters on board, go to all
                # else, go to clearing route to iteratively select recruiters
                if is_enough_reserve(self.player(request, game_id)):
                    to_recruit = unused_recruiters(
                        self.player(request, game_id)
                    ).count()
                    step = {
                        "faction": self.faction_string,
                        "name": "select_recruit_all",
                        "prompt": f"Confirm to recruit {to_recruit} warriors",
                        "endpoint": "recruit-all",
                        "payload_details": [{"type": "confirm", "name": "confirm"}],
                        "options": [{"value": "confirm", "label": "Confirm"}],
                    }
                else:
                    troops = troops_in_reserve(self.player(request, game_id))
                    step = {
                        "faction": self.faction_string,
                        "name": "select_recruit_clearing",
                        "prompt": f"Only {troops} warriors in reserve. Select recruiter clearing to recruit in.",
                        "endpoint": "recruit-clearing",
                        "payload_details": [
                            {
                                "type": "clearing_number",
                                "name": "recruiter_clearing_number",
                            }
                        ],
                    }
            case "birds-for-hire":
                step = {
                    "faction": self.faction_string,
                    "name": "select_birdsforhire_card",
                    "prompt": "Select a card to birds-for-hire",
                    "endpoint": "birdsforhire-card",
                    "payload_details": [{"type": "card", "name": "birdsforhire_card"}],
                }
            case _:
                raise ValidationError("Invalid action type")
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_march_clearing_origin(self, request, game_id: int):
        clearing_number = int(request.data["origin_clearing_number"])
        try:
            clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        # validate that there is a cat warrior in the clearing
        if not Warrior.objects.filter(
            clearing=clearing, player=self.player(request, game_id)
        ).exists():
            raise ValidationError({"detail": "No cat warrior in that clearing to move"})
        daylight = get_phase(self.player(request, game_id))
        assert type(daylight) == CatDaylight
        march_number = "first" if not daylight.midmarch else "second"
        step = {
            "faction": self.faction_string,
            "name": "select_move_clearing_destination",
            "prompt": f"Select a clearing to move to for {march_number} move of march.",
            "endpoint": "march-clearing-destination",
            "payload_details": [
                {"type": "clearing_number", "name": "destination_clearing_number"}
            ],
            "accumulated_payload": {
                "origin_clearing_number": clearing_number,
            },
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_march_clearing_destination(self, request, game_id: int):
        destination_clearing_number = int(request.data["destination_clearing_number"])
        origin_clearing_number = int(request.data["origin_clearing_number"])
        # validate rulership of either clearing
        origin_ruled_by_player = determine_clearing_rule(
            Clearing.objects.get(
                game=self.game(game_id), clearing_number=origin_clearing_number
            )
        ) == self.player(request, game_id)
        destination_ruled_by_player = determine_clearing_rule(
            Clearing.objects.get(
                game=self.game(game_id), clearing_number=destination_clearing_number
            )
        ) == self.player(request, game_id)
        if not origin_ruled_by_player and not destination_ruled_by_player:
            raise ValidationError(
                "Neither the origin or destination clearing is ruled by this player"
            )
        daylight = get_phase(self.player(request, game_id))
        assert type(daylight) == CatDaylight
        march_number = "first" if not daylight.midmarch else "second"
        step = {
            "faction": self.faction_string,
            "name": "select_move_warrior_count",
            "prompt": f"Select warriors to move for {march_number} move of march.",
            "endpoint": "march-count",
            "payload_details": [{"type": "number", "name": "warriors_to_move"}],
            "accumulated_payload": {
                "origin_clearing_number": origin_clearing_number,
                "destination_clearing_number": destination_clearing_number,
            },
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_march_count(self, request, game_id: int):
        # TODO: this whole view is too complex. should just call a transaction fucntion
        count = int(request.data["warriors_to_move"])
        origin_clearing = Clearing.objects.get(
            game=self.game(game_id),
            clearing_number=request.data["origin_clearing_number"],
        )
        destination_clearing = Clearing.objects.get(
            game=self.game(game_id),
            clearing_number=request.data["destination_clearing_number"],
        )
        if count < 1:
            raise ValidationError("Must select at least one warrior to move")
        warriors_in_origin = Warrior.objects.filter(
            player=self.player(request, game_id),
            clearing=origin_clearing,
        )
        if count > warriors_in_origin.count():
            raise ValidationError("Not enough warriors in origin clearing to move")
        try:
            atomic_game_action(cat_march)(
                self.player(request, game_id),
                origin_clearing,
                destination_clearing,
                count,
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # if first march, set midmarch to true and return the step for the beginning of a move

        daylight = get_phase(self.player(request, game_id))

        if not daylight.midmarch:
            step = {"faction": self.faction_string, "name": "completed"}
        else:  # march is done
            # go back to action selection
            step = {"faction": self.faction_string, "name": "completed"}
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_battle_clearing(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        clearing_number = int(request.data["battle_clearing_number"])
        defenders = self.validate_battle_clearing(game, player, clearing_number)
        options = [
            {"value": Faction(d.faction).value, "label": Faction(d.faction).label}
            for d in defenders
        ]
        step = {
            "faction": self.faction_string,
            "name": "select_defender",
            "prompt": "Select a defender",
            "endpoint": "battle-defender",
            "payload_details": [
                {"type": "faction", "name": "defender_faction"},
            ],
            "accumulated_payload": {
                "battle_clearing_number": clearing_number,
            },
            "options": options,
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_battle_defender(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        clearing_number = int(request.data["battle_clearing_number"])
        defender_faction = Faction(request.data["defender_faction"])
        print(defender_faction)
        defender = Player.objects.get(game=game, faction=defender_faction)
        valid_defenders = self.validate_battle_clearing(game, player, clearing_number)
        if defender not in valid_defenders:
            raise ValidationError("Not a valid defender - does not have pieces here")
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)

        try:
            atomic_game_action(cat_battle)(player, defender, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        return Response({"name": "completed"})

    def post_build_building(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        building_type_string = request.data["building_type"]
        # validate this building type is buildable (check that building is in the supply, and that enough wood is out of the supply that its theoretically possible)
        try:
            building_type = CatBuildingTypes(building_type_string.capitalize())
        except ValueError:
            raise ValidationError(
                f"Invalid building type. passed: {building_type_string}"
            )
        wood_cost = get_wood_cost(player, building_type)
        if wood_cost is None:
            raise ValidationError(f"No building of that type in supply")
        # validate that there is enough wood on the board
        wood_on_board = CatWood.objects.filter(
            player=player, clearing__isnull=False
        ).count()
        if wood_on_board < wood_cost:
            raise ValidationError(
                f"Not enough wood on board to build this building. Needed: {wood_cost}, on board: {wood_on_board}"
            )
        # all validated. proceed to clearing selection
        step = {
            "faction": self.faction_string,
            "name": "select_build_clearing",
            "prompt": "Select a clearing to build in",
            "endpoint": "build-clearing",
            "payload_details": [
                {"type": "clearing_number", "name": "build_clearing_number"},
            ],
            "accumulated_payload": {
                "building_type": building_type_string,
            },
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    @transaction.atomic
    def post_build_clearing(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        clearing_number = int(request.data["build_clearing_number"])
        building_type_string = request.data["building_type"]
        try:
            clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        try:
            building_type = CatBuildingTypes(building_type_string.capitalize())
        except KeyError:
            raise ValidationError(
                f"Invalid building type. passed: {building_type_string}"
            )
        # get usable wood tokens
        usable_wood = get_usable_wood_for_building(player, building_type, clearing)
        if usable_wood is None:
            raise ValidationError(f"Not enough connected wood to build")
        # if usable wood is precisely enough, build the building
        if len(usable_wood) == get_wood_cost(player, building_type):
            try:
                atomic_game_action(cat_build)(
                    player,
                    building_type,
                    clearing,
                    usable_wood,
                )
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return Response({"name": "completed"})
        else:
            # if not, go to wood selection step
            step = {
                "faction": self.faction_string,
                "name": "select_build_wood",
                "prompt": "Select wood to build with."
                + f" Needed: {get_wood_cost(player, building_type)}. Selected: 0",
                "endpoint": "build-wood",
                "payload_details": [
                    {"type": "clearing_number", "name": "wood_clearing_number"},
                ],
                "accumulated_payload": {
                    "building_type": building_type_string,
                    "build_clearing_number": clearing_number,
                    "wood_token_clearing_numbers": [],  # will track wood tokens to use
                },
            }
            serializer = GameActionStepSerializer(step)
            return Response(serializer.data)

    def post_build_wood(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        building_type_string = request.data["building_type"]
        try:
            building_type = CatBuildingTypes[building_type_string.upper()]
        except KeyError:
            raise ValidationError(
                f"Invalid building type. passed: {building_type_string}"
            )
        build_clearing_number = int(request.data["build_clearing_number"])
        try:
            clearing = Clearing.objects.get(
                game=game, clearing_number=build_clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        old_clearing_numbers = request.data["wood_token_clearing_numbers"]
        new_clearing_number = int(request.data["wood_clearing_number"])
        wood_count_by_clearing_number = {new_clearing_number: 1}
        for clearing_number in old_clearing_numbers:
            clearing_number = int(clearing_number)
            if clearing_number in wood_count_by_clearing_number:
                wood_count_by_clearing_number[clearing_number] += 1
            else:
                wood_count_by_clearing_number[clearing_number] = 1
        # get usable wood tokens
        total_wood: list[CatWood] = []
        for clearing_number in wood_count_by_clearing_number:
            wood_count = wood_count_by_clearing_number[clearing_number]
            woods = CatWood.objects.filter(
                clearing__game=game, clearing__clearing_number=clearing_number
            )[:wood_count]
            if len(woods) != wood_count:
                raise ValidationError(
                    f"More wood than exists selected in clearing {clearing_number}. Selected: {wood_count}, Existing: {len(woods)}"
                )
            total_wood.extend(woods)
        # if provided wood is precisely enough, build the building
        if len(total_wood) == get_wood_cost(player, building_type):

            try:
                atomic_game_action(cat_build)(
                    player,
                    building_type,
                    clearing,
                    total_wood,
                )
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return Response({"name": "completed"})
        # if not, continue wood selection step
        selected_wood_clearings = [int(c) for c in old_clearing_numbers] + [
            new_clearing_number
        ]
        step = {
            "faction": self.faction_string,
            "name": "select_build_wood",
            "prompt": "Select wood to build with."
            + f"Needed: {get_wood_cost(player, building_type)}. Selected: {len(total_wood)}",
            "endpoint": "build-wood",
            "payload_details": [
                {"type": "clearing_number", "name": "wood_clearing_number"},
            ],
            "accumulated_payload": {
                "building_type": building_type_string,
                "build_clearing_number": build_clearing_number,
                "wood_token_clearing_numbers": selected_wood_clearings,
            },
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_overwork_card(self, request, game_id: int):
        card_name = request.data["overwork_card"].upper().replace(" ", "_")
        card_data = CardsEP[card_name]
        validate_player_has_card_in_hand(self.player(request, game_id), card_data)
        # check that player has a sawmill in the correct colored suit
        textchoice_suit = card_data.value.suit

        sawmills = get_sawmills_by_suit(self.player(request, game_id), textchoice_suit)
        if not sawmills.exists():
            raise ValidationError("No sawmills in that suit")

        step = {
            "faction": self.faction_string,
            "name": "select_overwork_clearing",
            "prompt": "Select a clearing to overwork in",
            "endpoint": "overwork-clearing",
            "payload_details": [
                {"type": "clearing_number", "name": "overwork_clearing_number"}
            ],
            "accumulated_payload": {
                "overwork_card": card_name,
            },
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_overwork_clearing(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        clearing_number = int(request.data["overwork_clearing_number"])
        try:
            clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        card_name = request.data["overwork_card"].upper()
        card_data = CardsEP[card_name]
        try:
            atomic_game_action(overwork)(
                self.player(request, game_id), clearing, card_data
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        step = {
            "name": "completed",
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_recruit_all(self, request, game_id: int):
        try:
            atomic_game_action(cat_recruit_all)(self.player(request, game_id))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        step = {
            "name": "completed",
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_recruit_clearing(self, request, game_id: int):
        """
        need to step by step guide player thru selecting enough recruiters. once there are enough,
        use cat_recruit to place warriors at the selected recruiters
        """
        raise ValidationError("Not yet implemented")

    def post_birdsforhire_card(self, request, game_id: int):
        card_name = request.data["birdsforhire_card"].upper().replace(" ", "_")
        try:
            atomic_game_action(birds_for_hire)(
                self.player(request, game_id), CardsEP[card_name]
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        step = {
            "name": "completed",
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def end_step(self, request, game_id: int):
        player = self.player(request, game_id)
        atomic_game_action(end_action_step)(player)

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        # validate requesting player is cats first, since get_phase assumes the player is cats
        phase = get_phase(self.player(request, game_id))
        if type(phase) != CatDaylight:
            raise ValidationError("Not Daylight phase")
        if phase.step != CatDaylight.CatDaylightSteps.ACTIONS:
            raise ValidationError(
                "Wrong Step, not Actions Step. Current step: {phase.step.value}"
            )
        if get_current_player(self.game(game_id)) != self.player(request, game_id):
            raise ValidationError("Not this player's turn")

    def validate_battle_clearing(
        self, game: Game, player: Player, clearing_number: int
    ) -> list[Player]:
        """
        Validates that the clearing is valid to initiate a battle.
        Returns list of valid defenders.
        """
        try:
            clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        if not player_has_warriors_in_clearing(player, clearing):
            raise ValidationError(
                f"{self.faction_string} do not have warriors in that clearing"
            )
        # check that there are pieces of another player in the clearing
        players = Player.objects.filter(game=game)
        valid_defenders = []
        for player_ in players:
            if player_ != player:
                if player_has_pieces_in_clearing(player_, clearing):
                    valid_defenders.append(player_)
        if len(valid_defenders) == 0:
            raise ValidationError(f"No rival pieces in this clearing")
        return valid_defenders

    def cat_player(self, request, game_id: int):
        return Player.objects.get(game=self.game(game_id), faction=Faction.CATS)

    # def validate_player(self, request, game_id: int):
    #     """validate that player making a post request is the cat player"""
    #     player = self.player(request, game_id)
    #     if player != self.cat_player(request, game_id):
    #         raise ValidationError("Cat players turn, only they can make a move")
