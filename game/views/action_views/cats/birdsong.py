from game.models.cats.buildings import Sawmill
from game.models.cats.tokens import CatWood
from game.models.cats.turn import CatBirdsong
from game.models.game_models import Faction, Player
from game.queries.cats.turn import get_phase
from game.queries.cats.wood import get_unused_sawmill_by_clearing_number
from game.serializers.general_serializers import GameActionStepSerializer
from game.transactions.cats import cat_produce_all_wood, produce_wood
from game.decorators.transaction_decorator import atomic_game_action
from game.views.action_views.general import GameActionView
from django.db import transaction
from rest_framework.views import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status


class CatPlaceWoodView(GameActionView):
    action_name = "CAT_PLACE_WOOD"
    faction = Faction.CATS
    faction_string = Faction.CATS.label

    def player(self, request, game_id: int):

        return Player.objects.get(game=self.game(game_id), faction=Faction.CATS)

    def get(self, request):
        # check that more sawmills than wood tokens
        game_id = int(request.query_params.get("game_id"))
        game = self.game(game_id)
        print(game_id)
        player = Player.objects.get(game=game, faction=Faction.CATS)
        sawmill_count = Sawmill.objects.filter(player=player, used=False).count()
        wood_count = CatWood.objects.filter(player=player, clearing=None).count()
        step = self.determine_next_step(request, game_id)
        self.first_step = step
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        if route == "clearing":
            return self.post_clearing(request, game_id)
        elif route == "confirm_all":
            return self.post_confirm_all(request, game_id)
        return Response({"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST)

    def post_confirm_all(self, request, game_id: int):
        player = self.player(request, game_id)
        try:
            atomic_game_action(cat_produce_all_wood)(player)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return Response({"name": "completed"})

    def post_clearing(self, request, game_id: int):
        """
        places wood in selected clearing. returns same endpoint if more to place, or completed if no more
        No separate confirm step for this as of now.
        """
        player = self.player(request, game_id)
        clearing_number = int(request.data["wood_clearing_number"])
        sawmill = get_unused_sawmill_by_clearing_number(player, clearing_number)
        if sawmill is None:
            raise ValidationError({"detail": "No unused sawmill at that clearing"})
        try:
            atomic_game_action(produce_wood)(player, sawmill)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        step = self.determine_next_step(request, game_id)
        serializer = GameActionStepSerializer(step)
        return Response(serializer.data)

    def determine_next_step(self, request, game_id: int):
        player = Player.objects.get(game=self.game(game_id), faction=Faction.CATS)
        sawmill_count = Sawmill.objects.filter(player=player, used=False).count()
        wood_count = CatWood.objects.filter(player=player, clearing=None).count()

        if sawmill_count == 0:
            return {"name": "completed"}
        elif sawmill_count < wood_count:
            step = self.generate_step(
                name="place_all_wood",
                prompt="Confirm to place all wood",
                endpoint="confirm_all",
                payload_details=[{"type": "confirm", "name": "confirm"}],
                options=[{"value": True, "label": "Confirm"}],
            ).data
        else:
            step = self.generate_step(
                name="place_wood",
                prompt="Select clearings with sawmills for wood production."
                + f"{wood_count} wood tokens remaining",
                endpoint="clearing",
                payload_details=[{"type": "clearing_number", "name": "wood_clearing_number"}],
            ).data
            
        return step

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        """raises if not this player's turn or correct step"""
        phase = get_phase(self.player(self.request, game_id))
        if type(phase) != CatBirdsong:
            raise ValidationError("Not Birdsong phase")
        if phase.step != CatBirdsong.CatBirdsongSteps.PLACING_WOOD:
            raise ValidationError("Wrong Step. Current step: {phase.step.value}")
