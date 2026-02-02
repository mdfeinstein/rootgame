from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import Clearing, Faction, Player, CraftedCardEntry
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.general import validate_player_has_crafted_card
from game.transactions.crafted_cards.false_orders import use_false_orders
from game.queries.general import get_enemy_factions_in_clearing, get_adjacent_clearings
from game.decorators.transaction_decorator import atomic_game_action

class FalseOrdersView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = kwargs.get("game_id") or request.query_params.get("game_id")
        player = self.player(request, game_id)
        
        try:
            validate_player_has_crafted_card(player, CardsEP.FALSE_ORDERS)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        # Step 1: Pick origin clearing
        valid_clearings = []
        all_clearings = Clearing.objects.filter(game_id=game_id)
        for clearing in all_clearings:
            enemies = get_enemy_factions_in_clearing(player, clearing)
            if enemies:
                valid_clearings.append({
                    "value": str(clearing.clearing_number),
                    "label": f"Clearing {clearing.clearing_number} ({clearing.get_suit_display()})"
                })
        
        valid_clearings.append({"value": "skip", "label": "Skip"})
        
        return self.generate_step(
            name="pick-origin",
            prompt="Pick a clearing to move enemy warriors from",
            endpoint="pick-origin",
            payload_details=[{"type": "select", "name": "origin_number"}],
            options=valid_clearings,
            faction=Faction(player.faction)
        )

    def route_post(self, request, game_id: int, route: str, *args, **kwargs):
        match route:
            case "pick-origin":
                return self.post_pick_origin(request, game_id)
            case "pick-faction":
                return self.post_pick_faction(request, game_id)
            case "pick-destination":
                return self.post_pick_destination(request, game_id)
            case _:
                raise ValidationError("Invalid route")

    def post_pick_origin(self, request, game_id):
        player = self.player(request, game_id)
        origin_value = request.data["origin_number"]
        
        if origin_value == "skip":
            return self.generate_completed_step()
            
        origin_number = int(origin_value)
        origin = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=origin_number)
        
        enemies = get_enemy_factions_in_clearing(player, origin)
        options = []
        for enemy_faction in enemies:
            options.append({
                "value": enemy_faction.value,
                "label": enemy_faction.label
            })
            
        return self.generate_step(
            name="pick-faction",
            prompt="Pick an enemy faction to move",
            endpoint="pick-faction",
            payload_details=[{"type": "faction", "name": "target_faction"}],
            accumulated_payload={"origin_number": origin_number},
            options=options,
            faction=Faction(player.faction)
        )

    def post_pick_faction(self, request, game_id):
        player = self.player(request, game_id)
        origin_number = int(request.data["origin_number"])
        origin = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=origin_number)
        
        adjacent_clearings = get_adjacent_clearings(player, origin)
        options = []
        for adj in adjacent_clearings:
            options.append({
                "value": str(adj.clearing_number),
                "label": f"Clearing {adj.clearing_number} ({adj.get_suit_display()})"
            })
            
        return self.generate_step(
            name="pick-destination",
            prompt="Pick a destination clearing",
            endpoint="pick-destination",
            payload_details=[{"type": "clearing_number", "name": "destination_number"}],
            accumulated_payload={
                "origin_number": origin_number,
                "target_faction": request.data["target_faction"]
            },
            options=options,
            faction=Faction(player.faction)
        )

    def post_pick_destination(self, request, game_id):
        player = self.player(request, game_id)
        origin_number = int(request.data["origin_number"])
        target_faction_code = request.data["target_faction"]
        destination_number = int(request.data["destination_number"])
        
        origin = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=origin_number)
        destination = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=destination_number)
        target_player = Player.objects.get(game_id=game_id, faction=target_faction_code)
        
        crafted_card_entry = validate_player_has_crafted_card(player, CardsEP.FALSE_ORDERS)
        
        try:
            atomic_game_action(use_false_orders)(
                crafted_card_entry,
                target_player,
                origin,
                destination
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
            
        return self.generate_completed_step()
