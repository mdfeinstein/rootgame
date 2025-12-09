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
    get_unused_workshop_by_clearing_number,
    validate_unused_workshops_by_clearing_number,
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
from game.transactions.cats import action_used, birds_for_hire, build_building, overwork
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

    first_step = {
        "faction": faction_string,
        "name": "select_card",
        "prompt": "Select card to craft or choose nothing to end crafting step.",
        "endpoint": "card",
        "payload_details": [{"type": "card", "name": "card_to_craft"}],
    }

    def post(self, request, game_id: int, route: str):
        if route == "card":
            return self.post_card(request, game_id)
        elif route == "piece":
            return self.post_piece(request, game_id)
        elif route == "confirm":
            return self.post_confirm(request, game_id)

        return Response({"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST)

    def post_card(self, request, game_id: int):
        if request.data["card_to_craft"] is "":
            self.end_step(request, game_id)
            return Response({"name": "completed"})
        self.validate(request, game_id)
        serializer = GameActionStepSerializer(
            {
                "faction": self.faction_string,
                "name": "select_piece",
                "prompt": "Select a crafting piece to craft with",
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
        suits_needed, _ = self.validate(request, game_id)
        # check if we have enough pieces. if so, go to confirm. if not, go to piece
        accumulated_payload = [{"card_to_craft": request.data["card_to_craft"]}]
        cn_count = 0
        for key, value in request.data.items():
            if "cn_" in key:
                accumulated_payload.append({key: value})
                cn_count += 1

        if len(suits_needed) > 0:  # need to select more crafting pieces
            step = {
                "faction": self.faction_string,
                "name": "select_piece",
                "prompt": "Select a crafting piece to craft with",
                "endpoint": "piece",
                "payload_details": [
                    {"type": "clearing_number", "name": f"cn_{cn_count}"},
                ],
                "accumulated_payload": accumulated_payload,
            }
        else:  # we have all we need
            step = {
                "faction": self.faction_string,
                "name": "confirm",
                "prompt": "Confirm crafting",
                "endpoint": "confirm",
                "payload_details": [],
                "accumulated_payload": accumulated_payload,
            }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_confirm(self, request, game_id: int):
        _, crafting_pieces = self.validate(request, game_id)
        # craft
        card_type = CardsEP[request.data["card_to_craft"].upper()]
        card = Card.objects.get(game=self.game(game_id), card_type=card_type.name)
        card_in_hand = HandEntry.objects.get(
            player=self.player(request, game_id), card=card
        )
        craft_card(card_in_hand, crafting_pieces)

    def validate(self, request, game_id: int) -> tuple[list[Suit], list[Piece]]:
        # validate timing
        self.validate_timing(request, game_id)
        # validate card in hand and return card info
        card = self.validate_card(request, game_id)
        # get crafting pieces (or determine if not possible)
        suits_needed, crafting_pieces = self.validate_crafting_pieces(
            request, game_id, card
        )
        return suits_needed, crafting_pieces

    def validate_timing(self, request, game_id: int):
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
        card_info = request.data["card_to_craft"].upper()
        if card_info is None:
            raise ValidationError("No card selected")
        try:
            card_type = CardsEP[card_info].name
        except KeyError:
            raise ValidationError("Invalid card")
        card = Card.objects.get(game=self.game(game_id), card_type=card_type)
        if card is None:
            raise ValidationError("Card not found in game?")
        if not HandEntry.objects.filter(
            player=self.player(request, game_id), card=card
        ).exists():
            raise ValidationError("Card not in player's hand")
        # check that card is craftable
        card_details = CardsEP[card_info].value
        if card_details.craftable is False:
            raise ValidationError("Card is not craftable")
        return CardsEP[card_info]

    def validate_crafting_pieces(
        self, request, game_id: int, card: CardsEP
    ) -> tuple[list[Suit], list[Piece]]:
        """returns a tuple of (list of suits needed, list of crafting pieces)"""
        crafting_piece_clearing_numbers = {}  # clearing_number: piece_count
        for key, value in request.data.items():
            if "cn_" in key:
                try:
                    crafting_piece_clearing_numbers[value] += 1
                except KeyError:
                    crafting_piece_clearing_numbers[value] = 1
        game = self.game(game_id)
        player = self.player(request, game_id)
        # check that we have workshops in the given clearing numbers
        for clearing_number in crafting_piece_clearing_numbers:
            try:
                validate_unused_workshops_by_clearing_number(
                    player,
                    clearing_number,
                    crafting_piece_clearing_numbers[clearing_number],
                )
            except ValueError as e:
                raise ValidationError({"detail": str(e)})

        # compare the suits needed to the crafting pieces
        suits_needed = card.value.cost
        for clearing_number in crafting_piece_clearing_numbers:
            suit = Clearing.objects.get(game=game, clearing_number=clearing_number).suit
            for _ in range(len(crafting_piece_clearing_numbers[clearing_number])):
                suit_idx = suits_needed.index(suit)
                if suit_idx == -1:
                    suit_idx = suits_needed.index(Suit.WILD)
                    if suit_idx == -1:
                        raise ValueError(
                            "Selected crafting piece does not match crafting requirements"
                        )
                suits_needed.pop(suit_idx)
        crafting_pieces = []
        for clearing_number in crafting_piece_clearing_numbers:
            clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
            workshops = list(
                Workshop.objects.filter(player=player, building_slot__clearing=clearing)
            )
            crafting_pieces.extend(workshops)
        return suits_needed, crafting_pieces

    def end_step(self, request, game_id: int):
        player = self.player(request, game_id)
        daylight = get_phase(player)
        daylight.step = next_choice(CatDaylight.CatDaylightSteps, daylight.step)
        daylight.save()


class CatActionsView(GameActionView):
    action_name = "CAT_ACTIONS"
    faction_string = Faction.CATS.label

    first_step = {
        "faction": faction_string,
        "name": "select_action",
        "prompt": "Select action: march, battle, build, overwork, or birds-for-hire. Or, choose nothing to end action step.",
        "endpoint": "action",
        "payload_details": [{"type": "action_type", "name": "action"}],
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
                "prompt": "Select action: march, battle, build, overwork, or birds-for-hire. Or, choose nothing to end action step. "
                + f"Actions remaining: {daylight.actions_left}",
                "endpoint": "action",
                "payload_details": [{"type": "action_type", "name": "action"}],
            }
        self.first_step = step
        return super().get(request)

    def post(self, request, game_id: int, route: str):
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
            case "overwork-card":
                return self.post_overwork_card(request, game_id)
            case "overwork-clearing":
                return self.post_overwork_clearing(request, game_id)
            case "birdsforhire-card":
                return self.post_birdsforhire_card(request, game_id)
            case _:
                return Response(
                    {"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST
                )

    def post_action(self, request, game_id: int):
        self.validate_timing(request, game_id)
        if request.data["action"] is "":
            self.end_step(request, game_id)
            return Response({"name": "completed"})

        actions_remaining = get_actions_remaining(self.player(request, game_id))
        if actions_remaining == 0:
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
                }
            case "overwork":
                step = {
                    "faction": self.faction_string,
                    "name": "select_overwork_card",
                    "prompt": "Select a card to overwork",
                    "endpoint": "overwork-card",
                    "payload_details": [{"type": "card", "name": "overwork_card"}],
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
        self.validate_timing(request, game_id)
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
        self.validate_timing(request, game_id)
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

    @transaction.atomic
    def post_march_count(self, request, game_id: int):
        self.validate_timing(request, game_id)
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
            move_warriors(
                self.player(request, game_id),
                origin_clearing,
                destination_clearing,
                count,
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # if first march, set midmarch to true and return the step for the beginning of a move
        daylight = get_phase(self.player(request, game_id))
        if type(daylight) != CatDaylight:
            raise ValidationError("Not Daylight phase")
        if not daylight.midmarch:
            daylight.midmarch = True
            daylight.save()
            step = {
                "faction": self.faction_string,
                "name": "completed",
            }
        else:  # march is done
            # reduce actions remaining and reflip the march switch
            daylight.actions_left -= 1
            daylight.midmarch = False
            daylight.save()
            # go back to action selection
            step = {"faction": self.faction_string, "name": "completed"}
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_battle_clearing(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        self.validate_timing(request, game_id)
        clearing_number = int(request.data["battle_clearing_number"])
        self.validate_battle_clearing(game, player, clearing_number)
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
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    @transaction.atomic
    def post_battle_defender(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        self.validate_timing(request, game_id)
        clearing_number = int(request.data["battle_clearing_number"])
        defender_faction = get_choice_value_by_label_or_value(
            Faction, request.data["defender_faction"].capitalize()
        )
        print(defender_faction)
        defender = Player.objects.get(game=game, faction=defender_faction)
        valid_defenders = self.validate_battle_clearing(game, player, clearing_number)
        if defender not in valid_defenders:
            raise ValidationError("Not a valid defender - does not have pieces here")
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        start_battle(game, player.faction, defender.faction, clearing)
        daylight = get_phase(player)
        assert type(daylight) == CatDaylight
        daylight.actions_left -= 1
        daylight.save()

        return Response({"name": "completed"})

    def post_build_building(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        self.validate_timing(request, game_id)
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
        self.validate_timing(request, game_id)
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
                build_building(
                    player,
                    building_type,
                    clearing,
                    usable_wood,
                )
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            # update daylight step
            action_used(player)
            return Response({"name": "completed"})
        else:
            # if not, go to wood selection step
            step = {
                "faction": self.faction_string,
                "name": "select_build_wood",
                "prompt": "Select wood to build with."
                + f"Needed: {get_wood_cost(player, building_type)}. Selected: 0",
                "endpoint": "build-wood",
                "payload_details": [
                    {"type": "clearing_number", "name": "wood_clearing_number"},
                ],
                "accumulated_payload": {
                    "building_type": building_type_string,
                    "Build_clearing_number": clearing_number,
                    "wood_token_clearing_numbers": [],  # will track wood tokens to use
                },
            }
            serializer = GameActionStepSerializer(step)
            return Response(serializer.data)

    def post_build_wood(self, request, game_id: int):
        game = self.game(game_id)
        player = self.player(request, game_id)
        self.validate_timing(request, game_id)
        building_type_string = request.data["building_type"]
        try:
            building_type = CatBuildingTypes(building_type_string.upper())
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

            build_building(
                player,
                building_type,
                clearing,
                total_wood,
            )
            # update daylight step
            action_used(player)
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
                "Build_clearing_number": build_clearing_number,
                "wood_token_clearing_numbers": selected_wood_clearings,
            },
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_overwork_card(self, request, game_id: int):
        card_name = request.data["overwork_card"].upper().replace(" ", "_")
        card_data = CardsEP[card_name]
        self.validate_player(request, game_id)
        self.validate_timing(request, game_id)
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
        self.validate_timing(request, game_id)
        clearing_number = int(request.data["overwork_clearing_number"])
        try:
            clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        card_name = request.data["overwork_card"].upper()
        card_data = CardsEP[card_name]
        try:
            overwork(self.player(request, game_id), clearing, card_data)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        step = {
            "name": "completed",
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def post_birdsforhire_card(self, request, game_id: int):
        card_name = request.data["birdsforhire_card"].upper().replace(" ", "_")
        try:
            birds_for_hire(self.player(request, game_id), CardsEP[card_name])
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        step = {
            "name": "completed",
        }
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def end_step(self, request, game_id: int):
        player = self.player(request, game_id)
        daylight = get_phase(player)
        if type(daylight) != CatDaylight:
            raise ValidationError("Not Daylight phase")
        daylight.step = next_choice(CatDaylight.CatDaylightSteps, daylight.step)
        daylight.save()

    def validate_timing(self, request, game_id: int):
        """raises if not this player's turn or correct step"""
        # validate requesting player is cats first, since get_phase assumes the player is cats
        self.validate_player(request, game_id)
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

    def validate_player(self, request, game_id: int):
        """validate that player making a post request is the cat player"""
        player = self.player(request, game_id)
        if player != self.cat_player(request, game_id):
            raise ValidationError("Cat players turn, only they can make a move")
