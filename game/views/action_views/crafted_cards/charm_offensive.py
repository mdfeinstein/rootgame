from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import Faction, Player
from game.transactions.crafted_cards.charm_offensive import use_charm_offensive

class CharmOffensiveView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = request.query_params.get("game_id")
        player = self.player_by_request(request, game_id)
        self.faction = Faction(player.faction)
        
        # Get all other players to give a point to
        opponents = []
        other_players = Player.objects.filter(game_id=game_id).exclude(pk=player.pk)
        
        for p in other_players:
            faction = Faction(p.faction)
            opponents.append({
                "value": faction.label,
                "label": faction.label
            })
        opponents.append({
            "value": "skip",
            "label": "Skip"
        })
            
        self.first_step = {
            "faction": self.faction.label,
            "name": "pick-opponent",
            "prompt": "Pick an opponent to score one point, or skip.",
            "endpoint": "faction",
            "payload_details": [{"type": "faction", "name": "faction"}],
            "options": opponents
        }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "faction":
                if request.data["faction"] == "skip":
                    from game.transactions.crafted_cards.charm_offensive import skip_charm_offensive
                    player = self.player_by_request(request, game_id)
                    skip_charm_offensive(player)
                    return self.generate_completed_step()
                return self.post_pick_opponent(request, game_id)
            case _:
                return Response(status=status.HTTP_404_NOT_FOUND)

    def post_pick_opponent(self, request, game_id):
        player = self.player_by_request(request, game_id)
        faction_str = request.data["faction"]
        
        try:
            target_faction_key = faction_str.upper().replace(' ', '_')
            target_faction = Faction[target_faction_key]
        except KeyError:
             raise ValidationError({"detail": "Invalid faction"})
        
        # We can use Player.objects directly or helper if available
        try:
            opponent = Player.objects.get(game_id=game_id, faction=target_faction)
        except Player.DoesNotExist:
            raise ValidationError({"detail": "Opponent not found"})
        
        try:
            use_charm_offensive(player, opponent)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        
        return self.generate_completed_step()
