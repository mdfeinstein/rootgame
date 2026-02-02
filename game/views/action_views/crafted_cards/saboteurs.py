from game.queries.general import get_current_player
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import CraftedCardEntry, Faction, Player
from game.transactions.crafted_cards.saboteurs import use_saboteurs, saboteurs_skip
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.decorators.transaction_decorator import atomic_game_action

class SaboteursView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = kwargs.get("game_id") or request.query_params.get("game_id")
        player = self.player(request, game_id)
        
        # Step 1: Pick an enemy faction
        # Get factions that have crafted cards and are not the current player
        enemy_factions_with_cards = CraftedCardEntry.objects.filter(
            player__game_id=game_id
        ).exclude(player=player).values_list('player__faction', flat=True).distinct()
        
        options = []
        for faction_value in enemy_factions_with_cards:
            faction = Faction(faction_value)
            options.append({
                "value": faction.value,
                "label": faction.label
            })
        options.append({
            "value": "skip",
            "label": "Skip"
        })
            
        return self.generate_step(
            name="pick-faction",
            prompt="Pick an enemy faction to sabotage, or skip.",
            endpoint="pick-faction",
            payload_details=[{"type": "faction", "name": "opponent_faction"}],
            options=options,
            faction=Faction(player.faction)
        )

    def route_post(self, request, game_id: int, route: str, *args, **kwargs):
        match route:
            case "pick-faction":
                return self.post_pick_faction(request, game_id)
            case "pick-card":
                return self.post_pick_card(request, game_id)
            case _:
                raise ValidationError("Invalid route")

    def post_pick_faction(self, request, game_id):
        player = self.player(request, game_id)
        opponent_faction_value = request.data["opponent_faction"]
        
        if opponent_faction_value == "skip":
            try:
                atomic_game_action(saboteurs_skip)(player)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        target_faction = Faction(opponent_faction_value)
            
        if target_faction == Faction(player.faction):
            raise ValidationError({"detail": "You cannot sabotage yourself"})
            
        # Get crafted cards for this faction
        crafted_cards = CraftedCardEntry.objects.filter(
            player__game_id=game_id,
            player__faction=target_faction
        ).select_related('card')
        
        card_options = []
        for entry in crafted_cards:
            card_ep = entry.card.enum
            card_options.append({
                "value": card_ep.name,
                "label": card_ep.value.title
            })
            
        return self.generate_step(
            name="pick-card",
            prompt="Pick a card to discard",
            endpoint="pick-card",
            payload_details=[{"type": "card", "name": "card_name"}],
            accumulated_payload={"opponent_faction": opponent_faction_value},
            options=card_options,
            faction=Faction(player.faction)
        )

    def post_pick_card(self, request, game_id):
        player = self.player(request, game_id)
        opponent_faction_value = request.data["opponent_faction"]
        card_name = request.data["card_name"]
        
        target_faction = Faction(opponent_faction_value)
            
        try:
            card_ep = CardsEP[card_name]
        except KeyError:
            raise ValidationError({"detail": "Invalid card"})
            
        # Find the specific entry
        target_entry = CraftedCardEntry.objects.filter(
            player__game_id=game_id,
            player__faction=target_faction,
            card__card_type=card_ep.name
        ).first()
        
        if not target_entry:
            raise ValidationError({"detail": "Target card not found"})
            
        try:
            atomic_game_action(use_saboteurs)(player, target_entry)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        
        return self.generate_completed_step()
