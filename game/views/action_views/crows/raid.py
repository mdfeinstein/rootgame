from rest_framework import status
from rest_framework.exceptions import ValidationError
from game.models.game_models import Clearing, Faction
from game.models.events.event import Event
from game.models.events.crows import CrowRaidEvent
from game.queries.current_action.events import get_current_event
from game.transactions.crows.raid import place_raid_warrior
from game.decorators.transaction_decorator import atomic_game_action
from game.views.action_views.general import GameActionView

class CrowsPlaceRaidWarriorsView(GameActionView):
    action_name = "CROWS_PLACE_RAID_WARRIORS"
    faction = Faction.CROWS

    def get_first_step(self, player):
        event = get_current_event(player.game)
        if not event:
            return self.generate_completed_step()
            
        raid_event = CrowRaidEvent.objects.get(event=event)
        clearings = raid_event.remaining_clearings.all()
        
        return {
            "faction": self.faction.label,
            "name": "select_raid_clearing",
            "prompt": "Select adjacent clearing to place one Crow warrior (Raid effect).",
            "endpoint": "clearing",
            "payload_details": [{"type": "clearing_number", "name": "clearing_number"}],
            "options": [{"value": c.clearing_number, "label": c.name} for c in clearings],
        }

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        player = self.player_by_faction(request, game_id)
        self.first_step = self.get_first_step(player)
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        if route == "clearing":
            return self.post_clearing(request, game_id)
        raise ValidationError("Invalid route")

    def post_clearing(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        clearing_number = int(request.data["clearing_number"])
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
        event = get_current_event(game)
        
        try:
            atomic_game_action(place_raid_warrior)(player, clearing, event)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
            
        return self.generate_completed_step()

    def validate_timing(self, player: Player):
        event = get_current_event(player.game)
        if not event:
            raise ValidationError("No event currently")
        if event.type != EventType.PLACE_RAID_WARRIORS:
            raise ValidationError("Not a raid event")