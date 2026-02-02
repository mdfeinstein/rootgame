from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import Card, Clearing, Faction, Player, HandEntry
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.general import validate_player_has_card_in_hand, card_matches_clearing, get_enemy_factions_in_clearing
from game.transactions.crafted_cards.propaganda_bureau import use_propaganda_bureau
from game.decorators.transaction_decorator import atomic_game_action

class PropagandaBureauView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = kwargs.get("game_id") or request.query_params.get("game_id")
        player = self.player(request, game_id)
        
        options = []
        hand_entries = HandEntry.objects.filter(player=player).select_related('card')
        for entry in hand_entries:
            card_ep = entry.card.enum
            options.append({
                "value": card_ep.name,
                "label": f"{card_ep.value.suit.name} - {card_ep.value.title}" 
            })
            
        return self.generate_step(
            name="pick-card",
            prompt="Pick a card to spend for Propaganda Bureau",
            endpoint="pick-card",
            payload_details=[{"type": "card", "name": "card_name"}],
            options=options,
            faction=Faction(player.faction)
        )

    def route_post(self, request, game_id: int, route: str, *args, **kwargs):
        match route:
            case "pick-card":
                return self.post_pick_card(request, game_id)
            case "pick-clearing":
                return self.post_pick_clearing(request, game_id)
            case "pick-opponent":
                return self.post_pick_opponent(request, game_id)
            case _:
                raise ValidationError("Invalid route")

    def post_pick_card(self, request, game_id):
        player = self.player(request, game_id)
        card_name = request.data["card_name"]
        
        try:
            card_ep = CardsEP[card_name]
        except KeyError:
            raise ValidationError({"detail": "Invalid card"})
        
        try:
            validate_player_has_card_in_hand(player, card_ep)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})        

        # Generate clearing options for next step
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
            raise ValidationError({"detail": "No valid clearings with enemies match that suit"})
        
        return self.generate_step(
            name="pick-clearing",
            prompt="Pick a clearing to target",
            endpoint="pick-clearing",
            payload_details=[{"type": "clearing_number", "name": "clearing_number"}],
            accumulated_payload={"card_name": card_name},
            options=valid_clearings,
            faction=Faction(player.faction)
        )

    def post_pick_clearing(self, request, game_id):
        player = self.player(request, game_id)
        clearing_number = int(request.data["clearing_number"])
        clearing = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=clearing_number)
        
        enemies = get_enemy_factions_in_clearing(player, clearing)
        options = [
            {"value": enemy_faction.value, "label": enemy_faction.label}
            for enemy_faction in enemies
        ]
             
        return self.generate_step(
            name="pick-opponent",
            prompt="Pick an opponent to remove a warrior from",
            endpoint="pick-opponent",
            payload_details=[{"type": "faction", "name": "opponent_faction"}],
            accumulated_payload=request.data,
            options=options,
            faction=Faction(player.faction)
        )

    def post_pick_opponent(self, request, game_id):
        player = self.player(request, game_id)
        card_name = request.data["card_name"]
        clearing_number = int(request.data["clearing_number"])
        opponent_faction_value = request.data["opponent_faction"]
        
        card_ep = CardsEP[card_name]
        clearing = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=clearing_number)
        target_faction = Faction(opponent_faction_value)
        
        try:
             atomic_game_action(use_propaganda_bureau)(player, card_ep, clearing, target_faction)
        except ValueError as e:
             raise ValidationError({"detail": str(e)})
        
        return self.generate_completed_step()
