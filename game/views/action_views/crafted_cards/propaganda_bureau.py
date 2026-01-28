from rest_framework.exceptions import ValidationError
from game.queries.general import validate_player_has_card_in_hand
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import Card, Clearing, Faction, Player
from game.models.game_models import HandEntry, Warrior
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.serializers.general_serializers import GameActionStepSerializer
from game.transactions.crafted_cards.propaganda_bureau import use_propaganda_bureau

class PropagandaBureauView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = request.query_params.get("game_id")
        player = self.player_by_request(request, game_id)
        self.faction = Faction(player.faction) # Needed for generate_step helper
        
        cards = []
        hand_entries = HandEntry.objects.filter(player=player).select_related('card')
        
        for entry in hand_entries:
            card_ep = entry.card.enum
            cards.append({
                "value": card_ep.name,
                "label": f"{card_ep.value.suit.name} - {card_ep.name}" 
            })
            
        self.first_step = {
            "faction": self.faction.label,
            "name": "pick_card",
            "prompt": "Pick a card to spend for Propaganda Bureau",
            "endpoint": "pick_card",
            "payload_details": [{"type": "card", "name": "card_name"}],
            "options": cards
        }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "pick_card":
                return self.post_pick_card(request, game_id)
            case "pick_clearing":
                return self.post_pick_clearing(request, game_id)
            case "pick_opponent":
                return self.post_pick_opponent(request, game_id)
            case _:
                return Response(status=status.HTTP_404_NOT_FOUND)

    def post_pick_card(self, request, game_id):
        player = self.player_by_request(request, game_id)
        self.faction = Faction(player.faction)
        card_name = request.data["card_name"]
        
        try:
            card_ep = CardsEP[card_name]
        except KeyError:
            return Response({"error": "Invalid card"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            card_in_hand = validate_player_has_card_in_hand(player, card_ep)
        except ValueError as e:
            raise ValidationError({"details": str(e)})        
        # Generate clearing options for next step
        from game.queries.general import card_matches_clearing, get_enemy_factions_in_clearing
        
        valid_clearings = []
        all_clearings = Clearing.objects.filter(game_id=game_id)
        
        for clearing in all_clearings:
            if card_matches_clearing(card_ep, clearing):
                enemies = get_enemy_factions_in_clearing(player, clearing)
                if enemies:
                    valid_clearings.append({
                        "value": str(clearing.clearing_number),
                        "label": f"Clearing {clearing.clearing_number} ({clearing.get_suit_display()})"
                    })
        
        if not valid_clearings:
            raise ValidationError({"details": "No valid clearings match that suit"})
        
        return self.generate_step(
            name="pick_clearing",
            prompt="Pick a clearing to target",
            endpoint="pick_clearing",
            payload_details=[{"type": "clearing", "name": "clearing_number"}],
            accumulated_payload={"card_name": card_name},
            options=valid_clearings,
            faction=self.faction
        )

    def post_pick_clearing(self, request, game_id):
        player = self.player_by_request(request, game_id)
        self.faction = Faction(player.faction)
        
        card_name = request.data["card_name"]
        clearing_number = request.data["clearing_number"]
        clearing = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=clearing_number)
        
        from game.queries.general import get_enemy_factions_in_clearing
        enemies = get_enemy_factions_in_clearing(player, clearing)
        options = []
        for enemy_faction in enemies:
             options.append({
                 "value": enemy_faction.value,
                 "label": enemy_faction.label
             })
             
        return self.generate_step(
            name="pick_opponent",
            prompt="Pick an opponent to remove a warrior from",
            endpoint="pick_opponent",
            payload_details=[{"type": "faction", "name": "target_faction"}],
            accumulated_payload={
                "card_name": card_name, 
                "clearing_number": clearing_number
            },
            options=options,
            faction=self.faction
        )

    def post_pick_opponent(self, request, game_id):
        player = self.player_by_request(request, game_id)
        
        card_name = request.data["card_name"]
        clearing_number = request.data["clearing_number"]
        target_faction_code = request.data["target_faction"]
        
        card_ep = CardsEP[card_name]
        clearing = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=clearing_number)
        target_faction = Faction(target_faction_code)
        
        try:
             use_propaganda_bureau(player, card_ep, clearing, target_faction)
        except ValueError as e:
             print(f"DEBUG Propaganda Bureau ERROR: {str(e)}")
             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return self.generate_completed_step()
