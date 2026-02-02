from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import Faction, Player
from game.models.events.crafted_cards import CharmOffensiveEvent
from game.models.events.event import EventType
from game.queries.current_action.events import get_current_event
from game.transactions.crafted_cards.charm_offensive import use_charm_offensive, skip_charm_offensive
from game.decorators.transaction_decorator import atomic_game_action

class CharmOffensiveView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = kwargs.get("game_id") or request.query_params.get("game_id")
        player = self.player(request, game_id)
        
        # Get all other players to give a point to
        options = []
        other_players = Player.objects.filter(game_id=game_id).exclude(pk=player.pk)
        
        for p in other_players:
            faction = Faction(p.faction)
            options.append({
                "value": faction.value,
                "label": faction.label
            })
        
        options.append({
            "value": "skip",
            "label": "Skip"
        })
            
        return self.generate_step(
            name="pick-opponent",
            prompt="Pick an opponent to score one point, or skip.",
            endpoint="pick-opponent",
            payload_details=[{"type": "select", "name": "opponent_faction"}],
            options=options,
            faction=Faction(player.faction)
        )

    def route_post(self, request, game_id: int, route: str, *args, **kwargs):
        player = self.player(request, game_id)
        self.faction = Faction(player.faction)
        if route == "pick-opponent":
            return self.post_pick_opponent(request, game_id)
        raise ValidationError("Invalid route")

    def post_pick_opponent(self, request, game_id):
        player = self.player(request, game_id)
        opponent_faction_value = request.data["opponent_faction"]
        
        if opponent_faction_value == "skip":
            try:
                atomic_game_action(skip_charm_offensive)(player)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
            
        # Get opponent player
        try:
            opponent = Player.objects.get(game_id=game_id, faction=opponent_faction_value)
        except Player.DoesNotExist:
             raise ValidationError({"detail": "Opponent player not found"})
        
        try:
            atomic_game_action(use_charm_offensive)(player, opponent)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        
        return self.generate_completed_step()

    def get_event(self, game_id: int):
        event = get_current_event(self.game(game_id))
        try:
            return CharmOffensiveEvent.objects.get(event=event)
        except CharmOffensiveEvent.DoesNotExist:
             raise ValidationError({"detail": "Current Event not Charm Offensive"})

    def player(self, request, game_id: int) -> Player:
        event_entry = self.get_event(game_id)
        return event_entry.crafted_card_entry.player
    
    def validate_timing(self, request, game_id: int, route: str, *args, **kwargs):
        event = get_current_event(self.game(game_id))
        if not event or event.type != EventType.CHARM_OFFENSIVE:
            raise ValidationError({"detail": "Current Event not Charm Offensive"})
    
    def validate_player(self, request, game_id: int, route: str, *args, **kwargs):
        player = self.player(request, game_id)
        if player != self.player_by_request(request, game_id):
            raise ValidationError({"detail": "Not your turn"})
