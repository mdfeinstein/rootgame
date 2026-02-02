from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import Faction, Player
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
        opponent = get_object_or_404(Player, game_id=game_id, faction=opponent_faction_value)
        
        try:
            atomic_game_action(use_charm_offensive)(player, opponent)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        
        return self.generate_completed_step()
