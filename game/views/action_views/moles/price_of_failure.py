from rest_framework import status
from rest_framework.exceptions import ValidationError

from game.decorators.transaction_decorator import atomic_game_action
from game.errors import IllegalActionError, UnavailableActionError
from game.models.game_models import Faction
from game.models.moles.ministers import Minister
from game.queries.current_action.events import get_current_event
from game.transactions.moles.price_of_failure import resolve_price_of_failure
from game.views.action_views.general import GameActionView


class MolesPriceOfFailureView(GameActionView):
    action_name = "MOLES_PRICE_OF_FAILURE"
    faction = Faction.MOLES

    first_step = {
        "faction": Faction.MOLES.label,
        "name": "select_minister",
        "prompt": "Select a swayed minister to unsway.",
        "endpoint": "minister",
        "payload_details": [{"type": "minister_name", "name": "minister"}],
        "options": [],
    }

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        player = self.player(request, game_id)

        # Validate that current event is price of failure
        event = get_current_event(self.game(game_id))
        if not event or event.type != "price_of_failure":
            raise ValidationError("No Price of Failure event active")

        self.first_step = dict(self.first_step)
        self.first_step["options"] = self._get_minister_options(player)
        return super().get(request)

    def _get_minister_options(self, player):
        """Get swayed ministers of the highest available rank."""
        swayed = Minister.objects.filter(player=player, swayed=True)

        if not swayed.exists():
            return []

        # Determine highest rank among swayed ministers
        ranks = {}
        for minister in swayed:
            rank = minister.crown_type
            if rank not in ranks:
                ranks[rank] = []
            ranks[rank].append(minister)

        # Get highest rank (lord > noble > squire)
        highest_rank = None
        if "lord" in ranks:
            highest_rank = "lord"
        elif "noble" in ranks:
            highest_rank = "noble"
        else:
            highest_rank = "squire"

        # Build options for ministers of highest rank
        options = []
        for minister in ranks.get(highest_rank, []):
            options.append({
                "value": minister.name,
                "label": minister.get_name_display(),
            })

        return options

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "minister":
                return self.post_minister(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_minister(self, request, game_id: int):
        player = self.player(request, game_id)

        # Validate event
        event = get_current_event(self.game(game_id))
        if not event or event.type != "price_of_failure":
            raise ValidationError("No Price of Failure event active")

        minister_name_str = request.data.get("minister", "")
        if not minister_name_str:
            raise ValidationError("Minister is required")

        try:
            minister_enum = Minister.MinisterName(minister_name_str)
        except ValueError:
            raise ValidationError(f"Invalid minister: {minister_name_str}")

        try:
            atomic_game_action(resolve_price_of_failure)(player, minister_enum)
        except (IllegalActionError, UnavailableActionError) as e:
            raise ValidationError({"detail": str(e)})

        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, route: str, *args, **kwargs):
        """Validate that current event is a Price of Failure event."""
        event = get_current_event(self.game(game_id))
        if not event or event.type != "price_of_failure":
            raise ValidationError("No Price of Failure event active")
