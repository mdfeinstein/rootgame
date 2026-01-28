from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from game.views.action_views.general import GameActionView
from game.models.game_models import Faction, Suit
from game.models.events.crafted_cards import PartisansEvent
from game.transactions.battle import use_partisans, skip_partisans

class PartisansView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = request.query_params.get("game_id")
        player = self.player_by_request(request, game_id)
        
        event_entry = PartisansEvent.objects.filter(
            event__game_id=game_id, 
            event__is_resolved=False, 
            crafted_card_entry__player=player
        ).first()
        
        if not event_entry:
            raise ValidationError({"detail": "No active Partisans event for player."})
            
        clearing_suit = event_entry.battle.clearing.suit
        suit_name = Suit(clearing_suit).label
        
        options = [
            {"value": "use", "label": "Use Partisans"},
            {"value": "skip", "label": "Skip"}
        ]
        
        self.faction = Faction(player.faction)
        self.first_step = {
            "faction": self.faction.label,
            "name": "use-or-skip",
            "prompt": f"Do you want to use Partisans to deal an extra hit? (You will discard all cards except {suit_name} cards)",
            "endpoint": "use-or-skip",
            "payload_details": [{"type": "choice", "name": "choice"}],
            "options": options,
            "accumulated_payload": {"event_entry_id": event_entry.id}
        }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "use-or-skip":
                return self.post_use_or_skip(request, game_id)
            case _:
                return Response(status=status.HTTP_404_NOT_FOUND)

    def post_use_or_skip(self, request, game_id):
        player = self.player_by_request(request, game_id)
        choice = request.data["choice"]
        event_entry_id = request.data["event_entry_id"]
        event_entry = get_object_or_404(PartisansEvent, id=event_entry_id, crafted_card_entry__player=player)
        match choice:
            case "skip":
                skip_partisans(event_entry.battle.clearing.game, event_entry.battle, event_entry)
            case "use":
                use_partisans(event_entry.battle.clearing.game, event_entry.battle, event_entry)
            case _:
                raise ValidationError({"detail": f"Invalid choice: {choice}"})
        return self.generate_completed_step()
