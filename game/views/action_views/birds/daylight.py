from game.models.birds.buildings import BirdRoost
from game.models.birds.player import DecreeEntry
from game.models.birds.turn import BirdDaylight
from game.models.game_models import Faction
from game.queries.birds.decree import get_decree_entry_to_use
from game.queries.birds.turn import validate_step
from game.transactions.birds import bird_recruit_action, next_daylight_step
from game.views.action_views.general import GameActionView
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView


class BirdCraftingView(GameActionView):
    action_name = "BIRDS_CRAFTING"
    faction = Faction.BIRDS

    first_step = {
        "faction": faction,
        "name": "select_card",
        "prompt": "Select card to craft or choose nothing to end crafting step.",
        "endpoint": "card",
        "payload_details": [{"type": "card", "name": "card_to_craft"}],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "card":
            return self.post_card(request, game_id)
        elif route == "piece":
            return self.post_piece(request, game_id)
        else:
            raise ValueError("Invalid route")

    def post_card(self, request, game_id: int):
        if request.data["card_to_craft"] == "":
            try:
                next_daylight_step(self.player(request, game_id))
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        # TODO: implement crafting
        pass

    def post_piece(self, request, game_id: int):
        pass

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, BirdDaylight.BirdDaylightSteps.CRAFTING)


class BirdRecruitView(GameActionView):
    action_name = "BIRDS_RECRUIT"
    faction = Faction.BIRDS

    first_step = {
        "faction": faction,
        "name": "select_recruit_clearing",
        "prompt": "Select clearing to recruit in.",
        "endpoint": "clearing",
        "payload_details": [{"type": "clearing_number", "name": "recruit_clearing"}],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "clearing":
            return self.post_clearing(request, game_id)
        else:
            raise ValueError("Invalid route")

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
        decree_to_use = get_decree_entry_to_use(
            player, DecreeEntry.Column.RECRUIT, roost.building_slot.clearing.suit
        )
        try:
            bird_recruit_action(player, roost, decree_to_use)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, BirdDaylight.BirdDaylightSteps.RECRUITING)
