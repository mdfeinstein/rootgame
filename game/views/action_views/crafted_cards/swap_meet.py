from rest_framework.response import Response
from game.views.action_views.general import GameActionView
from game.serializers.general_serializers import GameActionStepSerializer
from game.models.game_models import Player, Faction, HandEntry, Card
from game.models.events.crafted_cards import SwapMeetEvent
from game.transactions.crafted_cards.swap_meet import swap_meet_take_card, swap_meet_give_card
from game.game_data.cards.exiles_and_partisans import CardsEP
from django.shortcuts import get_object_or_404

class SwapMeetPickOpponentView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = kwargs.get("game_id") or request.query_params.get("game_id")
        game = self.game(game_id)
        player = self.player(request, game_id)
        
        # Options: players with cards in hand
        opponents = Player.objects.filter(game=game).exclude(id=player.id)
        options = []
        for opponent in opponents:
            hand_count = HandEntry.objects.filter(player=opponent).count()
            faction = Faction(opponent.faction)
            if hand_count > 0:
                options.append({
                    "value": faction.value,
                    "label": f"{faction.label} ({hand_count} cards)"
                })
        return self.generate_step(
            "pick-opponent",
            "Pick a player to take a random card from.",
            "pick-opponent",
            [{"type": "select", "name": "opponent_faction"}],
            options=options,
            faction=Faction(player.faction).label,
        )

    def post(self, request, game_id: int, route: str, *args, **kwargs):
        player = self.player(request, game_id)
        opponent_faction = request.data["opponent_faction"]
        opponent = get_object_or_404(Player, game=self.game(game_id), faction=opponent_faction)
        
        swap_meet_take_card(player, opponent)
        
        return Response({"name": "completed"})

class SwapMeetGiveCardView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = kwargs.get("game_id") or request.query_params.get("game_id")
        game = self.game(game_id)
        player = self.player(request, game_id)
        
        # Options: player's hand
        hand = HandEntry.objects.filter(player=player).select_related('card')
        options = [
            {"value": entry.card.card_type, "label": entry.card.title}
            for entry in hand
        ]
        
        step = {
            "faction": player.faction,
            "name": "pick-card-to-give",
            "prompt": "Pick a card to give back.",
            "endpoint": "pick-card-to-give",
            "payload_details": [
                {
                    "type": "card",
                    "name": "card_name",
                    "options": options
                }
            ]
        }
        return Response(GameActionStepSerializer(step).data)

    def post(self, request, game_id: int, route: str, *args, **kwargs):
        player = self.player(request, game_id)
        card_name = request.data["card_name"]
        
        try:
            card_ep = CardsEP[card_name.upper()]
        except KeyError:
            raise ValidationError({"detail": "Invalid card"})
            
        # Find active swap meet event for this player
        event = (
            SwapMeetEvent.objects.filter(
                taking_player=player, 
                event__is_resolved=False
            )
            .order_by("-event__created_at")
            .first()
        )
        
        if not event:
            raise ValueError("No active Swap Meet event found")
            
        swap_meet_give_card(event, card_ep)
        
        return Response({"name": "completed"})
