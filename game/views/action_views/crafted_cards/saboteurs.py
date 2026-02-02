from game.queries.general import get_current_player
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import CraftedCardEntry, Faction, Player
from game.transactions.crafted_cards.saboteurs import use_saboteurs
from game.game_data.cards.exiles_and_partisans import CardsEP

class SaboteursView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = request.query_params.get("game_id")
        game = self.game(game_id)
        player = get_current_player(game)
        self.faction = Faction(player.faction)
        
        # Step 1: Pick an enemy faction
        # Get factions that have crafted cards and are not the current player
        enemy_factions_with_cards = CraftedCardEntry.objects.filter(
            player__game_id=game_id
        ).exclude(player=player).values_list('player__faction', flat=True).distinct()
        
        faction_options = []
        for faction_code in enemy_factions_with_cards:
            faction = Faction(faction_code)
            faction_options.append({
                "value": faction.name, # "Birds", "Cats", "Woodland Alliance"
                "label": faction.label
            })
        faction_options.append({
            "value": "skip",
            "label": "Skip"
        })
            
        self.first_step = {
            "faction": self.faction.label,
            "name": "pick-faction",
            "prompt": "Pick an enemy faction to sabotage, or skip.",
            "endpoint": "pick-faction",
            "payload_details": [{"type": "faction", "name": "faction"}],
            "options": faction_options
        }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "pick-faction":
                if request.data["faction"] == "skip":
                    from game.transactions.crafted_cards.saboteurs import saboteurs_skip
                    player = self.player_by_request(request, game_id)
                    saboteurs_skip(player)
                    return self.generate_completed_step()
                return self.post_pick_faction(request, game_id)
            case "card":
                return self.post_pick_card(request, game_id)
            case _:
                return Response(status=status.HTTP_404_NOT_FOUND)

    def post_pick_faction(self, request, game_id):
        player = self.player_by_request(request, game_id)
        self.faction = Faction(player.faction)
        faction_str = request.data["faction"]
        
        # Convert "Woodland Alliance" -> Faction.WOODLAND_ALLIANCE
        try:
            target_faction_key = faction_str.upper().replace(' ', '_')
            target_faction = Faction[target_faction_key]
        except KeyError:
            raise ValidationError({"detail": "Invalid faction"})
            
        if target_faction == self.faction:
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
                "value": card_ep.name, # e.g. FOXFOLK_STEEL
                "label": card_ep.value.title
            })
            
        return self.generate_step(
            name="pick-card",
            prompt="Pick a card to discard",
            endpoint="card", # User requested endpoint to be "card"
            payload_details=[{"type": "card", "name": "card"}],
            accumulated_payload={"faction": faction_str},
            options=card_options,
            faction=self.faction
        )

    def post_pick_card(self, request, game_id):
        player = self.player_by_request(request, game_id)
        faction_str = request.data["faction"]
        card_str = request.data["card"]
        
        try:
            target_faction_key = faction_str.upper().replace(' ', '_')
            target_faction = Faction[target_faction_key]
        except KeyError:
            raise ValidationError({"detail": "Invalid faction"})
            
        try:
            card_ep = CardsEP[card_str.upper()]
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
            use_saboteurs(player, target_entry)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        
        return self.generate_completed_step()
