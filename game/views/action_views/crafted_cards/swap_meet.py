from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from game.views.action_views.general import GameActionView
from game.models.game_models import Player, Faction, HandEntry
from game.models.events.crafted_cards import SwapMeetEvent
from game.transactions.crafted_cards.swap_meet import swap_meet_take_card, swap_meet_give_card
from game.game_data.cards.exiles_and_partisans import CardsEP
from django.shortcuts import get_object_or_404
from game.decorators.transaction_decorator import atomic_game_action

class SwapMeetView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = kwargs.get("game_id") or request.query_params.get("game_id")
        player = self.player(request, game_id)
        
        # Check for active event
        event = SwapMeetEvent.objects.filter(
            taking_player=player, 
            event__is_resolved=False
        ).first()
        
        if event:
            return self.get_pick_card_to_give(player)
        else:
            return self.get_pick_opponent(player, game_id)

    def get_pick_opponent(self, player, game_id):
        game = self.game(game_id)
        opponents = Player.objects.filter(game=game).exclude(id=player.id)
        options = []
        for opponent in opponents:
            hand_count = HandEntry.objects.filter(player=opponent).count()
            if hand_count > 0:
                faction = Faction(opponent.faction)
                options.append({
                    "value": faction.value,
                    "label": f"{faction.label} ({hand_count} cards)"
                })
        
        return self.generate_step(
            name="pick-opponent",
            prompt="Pick a player to take a random card from.",
            endpoint="pick-opponent",
            payload_details=[{"type": "select", "name": "opponent_faction"}],
            options=options,
            faction=Faction(player.faction)
        )

    def get_pick_card_to_give(self, player):
        hand = HandEntry.objects.filter(player=player).select_related('card')
        options = [
            {"value": entry.card.card_type, "label": entry.card.title}
            for entry in hand
        ]
        
        return self.generate_step(
            name="pick-card-to-give",
            prompt="Pick a card to give back.",
            endpoint="pick-card-to-give",
            payload_details=[{"type": "card", "name": "card_name"}],
            options=options,
            faction=Faction(player.faction)
        )

    def route_post(self, request, game_id: int, route: str, *args, **kwargs):
        if route == "pick-opponent":
            return self.post_pick_opponent(request, game_id)
        if route == "pick-card-to-give":
            return self.post_pick_card_to_give(request, game_id)
        raise ValidationError("Invalid route")

    def post_pick_opponent(self, request, game_id: int):
        player = self.player(request, game_id)
        opponent_faction_value = request.data["opponent_faction"]
        game = self.game(game_id)
        opponent = get_object_or_404(Player, game=game, faction=opponent_faction_value)
        
        try:
            atomic_game_action(swap_meet_take_card)(player, opponent)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
            
        return self.get_pick_card_to_give(player)

    def post_pick_card_to_give(self, request, game_id: int):
        player = self.player(request, game_id)
        card_name = request.data["card_name"]
        
        try:
            card_ep = CardsEP[card_name.upper()]
        except (KeyError, AttributeError):
            raise ValidationError({"detail": "Invalid card"})
            
        event = SwapMeetEvent.objects.filter(
            taking_player=player, 
            event__is_resolved=False
        ).first()
        
        if not event:
            raise ValidationError({"detail": "No active Swap Meet event found"})
            
        try:
            atomic_game_action(swap_meet_give_card)(event, card_ep)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
            
        return self.generate_completed_step()
