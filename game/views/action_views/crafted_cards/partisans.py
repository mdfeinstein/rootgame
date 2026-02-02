from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import Faction, Suit
from game.models.events.crafted_cards import PartisansEvent
from game.transactions.battle import use_partisans, skip_partisans
from game.decorators.transaction_decorator import atomic_game_action

class PartisansView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = kwargs.get("game_id") or request.query_params.get("game_id")
        player = self.player(request, game_id)
        
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
        
        return self.generate_step(
            name="use-or-skip",
            prompt=f"Do you want to use Partisans to deal an extra hit? (You will discard all cards except {suit_name} cards)",
            endpoint="use-or-skip",
            payload_details=[{"type": "choice", "name": "selection"}],
            options=options,
            faction=Faction(player.faction)
        )

    def route_post(self, request, game_id: int, route: str, *args, **kwargs):
        match route:
            case "use-or-skip":
                return self.post_use_or_skip(request, game_id)
            case _:
                raise ValidationError("Invalid route")

    def post_use_or_skip(self, request, game_id):
        player = self.player(request, game_id)
        choice = request.data["selection"]
        
        event_entry = PartisansEvent.objects.filter(
            event__game_id=game_id, 
            event__is_resolved=False, 
            crafted_card_entry__player=player
        ).first()
        
        if not event_entry:
             raise ValidationError("No active event")

        match choice:
            case "skip":
                try:
                    atomic_game_action(skip_partisans)(event_entry.battle.clearing.game, event_entry.battle, event_entry)
                except ValueError as e:
                    raise ValidationError({"detail": str(e)})
            case "use":
                try:
                    atomic_game_action(use_partisans)(event_entry.battle.clearing.game, event_entry.battle, event_entry)
                except ValueError as e:
                    raise ValidationError({"detail": str(e)})
            case _:
                raise ValidationError({"detail": f"Invalid choice: {choice}"})
        return self.generate_completed_step()
