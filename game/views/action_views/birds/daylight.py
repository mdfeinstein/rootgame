from game.queries.general import get_enemy_factions_in_clearing
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.game_data.general.game_enums import Suit
from game.models.birds.buildings import BirdRoost
from game.models.birds.player import DecreeEntry
from game.models.birds.turn import BirdDaylight
from game.models.game_models import Clearing, Faction, Player
from game.queries.birds.crafting import (
    is_able_to_be_crafted,
    validate_crafting_pieces_satisfy_requirements,
)
from game.queries.birds.decree import get_decree_entry_to_use
from game.queries.birds.roosts import roost_at_clearing_number
from game.queries.birds.turn import validate_step
from game.queries.general import (
    validate_enemy_pieces_in_clearing,
    validate_has_legal_moves,
    validate_legal_move,
)
from game.transactions.battle import start_battle
from game.transactions.birds import (
    bird_battle_action,
    bird_build_action,
    bird_craft_card,
    bird_move_action,
    bird_recruit_action,
    next_daylight_step,
)
from game.decorators.transaction_decorator import atomic_game_action
from game.views.action_views.general import GameActionView
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


class BirdCraftingView(GameActionView):
    action_name = "BIRDS_CRAFTING"
    faction = Faction.BIRDS

    first_step = {
        "faction": faction.label,
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
        else:
            raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_card(self, request, game_id: int):
        if request.data["card_to_craft"] == "":
            try:
                atomic_game_action(next_daylight_step)(self.player(request, game_id))
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        # TODO: implement crafting
        card = CardsEP[request.data["card_to_craft"]]
        if not is_able_to_be_crafted(self.player(request, game_id), card):
            raise ValidationError("Not enough crafting pieces to craft this card")
        suits_needed = [cost.label for cost in card.value.cost]
        prompt = f"Select {(suits_needed)} crafting pieces to craft this card."
        return self.generate_step(
            "select_pieces",
            prompt,
            "piece",
            [{"type": "clearing_number", "name": "roost_clearing_number"}],
            {
                "card_to_craft": request.data["card_to_craft"],
                "roost_clearing_numbers": [],
            },
        )

    def post_piece(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        card = CardsEP[request.data["card_to_craft"]]
        old_clearing_numbers = request.data["roost_clearing_numbers"]
        new_clearing_number = int(request.data["roost_clearing_number"])
        clearing_numbers = old_clearing_numbers + [new_clearing_number]
        try:
            roosts = [
                roost_at_clearing_number(player, clearing_number)
                for clearing_number in clearing_numbers
            ]
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        try:
            all_pieces_satisfied = validate_crafting_pieces_satisfy_requirements(
                player, card, roosts
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        if all_pieces_satisfied:
            # try to craft
            try:
                atomic_game_action(bird_craft_card)(player, card, roosts)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        # otherwise, continue to select pieces
        suits_needed = [cost.label for cost in card.value.cost]
        suits_selected = [
            Suit(roost.building_slot.clearing.suit).label for roost in roosts
        ]
        prompt = f"Select more crafting pieces to craft this card. Needed: {suits_needed}. Selected: {suits_selected}"
        return self.generate_step(
            "select_pieces",
            prompt,
            "piece",
            [{"type": "clearing_number", "name": "roost_clearing_number"}],
            {
                "card_to_craft": request.data["card_to_craft"],
                "roost_clearing_numbers": clearing_numbers,
            },
        )

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, BirdDaylight.BirdDaylightSteps.CRAFTING)


class BirdRecruitView(GameActionView):
    action_name = "BIRDS_RECRUIT"
    faction = Faction.BIRDS

    first_step = {
        "faction": faction.label,
        "name": "select_recruit_clearing",
        "prompt": "Select clearing to recruit in.",
        "endpoint": "clearing",
        "payload_details": [{"type": "clearing_number", "name": "recruit_clearing"}],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "clearing":
            return self.post_clearing(request, game_id)
        else:
            raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_clearing(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_number = int(request.data["recruit_clearing"])
        try:
            roost = BirdRoost.objects.get(
                player=player, building_slot__clearing__clearing_number=clearing_number
            )
        except BirdRoost.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        # figure out which decree entry to use
        try:
            decree_to_use = get_decree_entry_to_use(
                player, DecreeEntry.Column.RECRUIT, roost.building_slot.clearing.suit
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        try:
            atomic_game_action(bird_recruit_action)(player, roost, decree_to_use)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, BirdDaylight.BirdDaylightSteps.RECRUITING)


class BirdMoveView(GameActionView):
    action_name = "BIRDS_MOVE"
    faction = Faction.BIRDS

    first_step = {
        "faction": faction.label,
        "name": "select_origin",
        "prompt": "Select origin clearing",
        "endpoint": "origin",
        "payload_details": [{"type": "clearing_number", "name": "origin_clearing"}],
    }

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
        clearing_number = int(request.data["origin_clearing"])
        try:
            clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        try:
            validate_has_legal_moves(player, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_step(
            "destination",
            f"Select destination clearing.",
            "destination",
            [
                {"type": "clearing_number", "name": "destination_clearing"},
            ],
            {"origin_clearing": clearing_number},
        )

    def post_destination(self, request, game_id: int):
        player = self.player(request, game_id)
        origin_clearing_number = int(request.data["origin_clearing"])
        destination_clearing_number = int(request.data["destination_clearing"])
        try:
            origin_clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=origin_clearing_number
            )
            destination_clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=destination_clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        try:
            validate_legal_move(player, origin_clearing, destination_clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        accumulated_payload = {
            "origin_clearing": origin_clearing_number,
            "destination_clearing": destination_clearing_number,
        }
        return self.generate_step(
            "count",
            f"Select number of pieces to move.",
            "count",
            [
                {"type": "number", "name": "count"},
            ],
            accumulated_payload,
        )

    def post_count(self, request, game_id: int):
        player = self.player(request, game_id)
        origin_clearing_number = int(request.data["origin_clearing"])
        destination_clearing_number = int(request.data["destination_clearing"])
        count = int(request.data["count"])
        try:
            origin_clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=origin_clearing_number
            )
            destination_clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=destination_clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        decree = get_decree_entry_to_use(
            player, DecreeEntry.Column.MOVE, origin_clearing.suit
        )
        # call move transaction
        try:
            atomic_game_action(bird_move_action)(
                player, origin_clearing, destination_clearing, count, decree
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, BirdDaylight.BirdDaylightSteps.MOVING)


class BirdBattleView(GameActionView):
    action_name = "BIRDS_BATTLE"
    faction = Faction.BIRDS

    first_step = {
        "faction": faction.label,
        "name": "select_clearing",
        "prompt": "Select clearing to battle in.",
        "endpoint": "clearing",
        "payload_details": [{"type": "clearing_number", "name": "clearing"}],
    }

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
        clearing_number = int(request.data["clearing"])
        try:
            clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        # see if there is a decree that works for this clearing
        try:
            get_decree_entry_to_use(player, DecreeEntry.Column.BATTLE, clearing.suit)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # check that there are enemy pieces in the clearing
        try:
            validate_enemy_pieces_in_clearing(player, clearing)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        enemy_factions = get_enemy_factions_in_clearing(player, clearing)
        options = [{"value": faction.name, "label": faction.label} for faction in enemy_factions]
        return self.generate_step(
            "faction",
            f"Select faction to battle.",
            "faction",
            [
                {"type": "faction", "name": "faction"},
            ],
            {"clearing": clearing_number},
            options=options,
        )

    def post_faction(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_number = int(request.data["clearing"])
        faction_string = request.data["faction"]
        faction = Faction[faction_string]
        try:
            clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        try:
            defender = Player.objects.get(game=self.game(game_id), faction=faction)
        except Player.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        # get decree entry to use
        try:
            decree_to_use = get_decree_entry_to_use(
                player, DecreeEntry.Column.BATTLE, clearing.suit
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # call bird battle transaction
        try:
            atomic_game_action(bird_battle_action)(player, defender, clearing, decree_to_use)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, BirdDaylight.BirdDaylightSteps.BATTLING)


class BirdBuildingView(GameActionView):
    action_name = "BIRDS_BUILDING"
    faction = Faction.BIRDS

    first_step = {
        "faction": faction.label,
        "name": "select_clearing",
        "prompt": "Select clearing to build in",
        "endpoint": "clearing",
        "payload_details": [{"type": "clearing_number", "name": "clearing"}],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "clearing":
            return self.post_clearing(request, game_id)
        raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_clearing(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_number = int(request.data["clearing"])
        try:
            clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=clearing_number
            )
        except Clearing.DoesNotExist as e:
            raise ValidationError({"detail": str(e)})
        # get decree entry to use
        try:
            decree_to_use = get_decree_entry_to_use(
                player, DecreeEntry.Column.BUILD, clearing.suit
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        # call bulding transaction
        try:
            atomic_game_action(bird_build_action)(player, clearing, decree_to_use)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, BirdDaylight.BirdDaylightSteps.BUILDING)
