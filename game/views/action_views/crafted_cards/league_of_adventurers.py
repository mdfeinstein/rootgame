from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import CraftedItemEntry, Faction, Player, Clearing, Warrior
from game.transactions.crafted_cards.league_of_adventurers import use_league_of_adventurers
from game.queries.general import warrior_count_in_clearing, player_has_warriors_in_clearing, player_has_pieces_in_clearing

class LeagueOfAdventurersView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = request.query_params.get("game_id")
        player = self.player_by_request(request, game_id)
        self.faction = Faction(player.faction)
        
        # Step 1: Pick an item to exhaust
        items = CraftedItemEntry.objects.filter(player=player, exhausted=False).select_related('item')
        item_options = []
        for entry in items:
            item_options.append({
                "value": str(entry.id),
                "label": entry.item.get_item_type_display()
            })
            
        if not item_options:
            raise ValidationError({"detail": "No items available to exhaust."})

        self.first_step = {
            "faction": self.faction.label,
            "name": "pick-item",
            "prompt": "Pick an item to exhaust for League of Adventurers",
            "endpoint": "pick-item",
            "payload_details": [{"type": "crafted_item", "name": "item_id"}],
            "options": item_options
        }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "pick-item":
                return self.post_pick_item(request, game_id)
            case "pick-action":
                return self.post_pick_action(request, game_id)
            case "pick-origin":
                return self.post_pick_origin(request, game_id)
            case "pick-destination":
                return self.post_pick_destination(request, game_id)
            case "pick-count":
                return self.post_pick_count(request, game_id)
            case "pick-clearing":
                return self.post_pick_clearing(request, game_id)
            case "pick_clearing": # Allow both hyphens and underscores just in case
                return self.post_pick_clearing(request, game_id)
            case "pick-opponent":
                return self.post_pick_opponent(request, game_id)
            case _:
                return Response(status=status.HTTP_404_NOT_FOUND)

    def post_pick_item(self, request, game_id):
        player = self.player_by_request(request, game_id)
        item_id = request.data["item_id"]
        
        # Verify item exists and belongs to player
        get_object_or_404(CraftedItemEntry, pk=item_id, player=player, exhausted=False)
        
        options = [
            {"value": "move", "label": "Move"},
            {"value": "battle", "label": "Battle"}
        ]
        
        return self.generate_step(
            name="pick-action",
            prompt="Choose an action to perform",
            endpoint="pick-action",
            payload_details=[{"type": "action", "name": "action_type"}],
            accumulated_payload={"item_id": item_id},
            options=options,
            faction=Faction(player.faction)
        )

    def post_pick_action(self, request, game_id):
        player = self.player_by_request(request, game_id)
        item_id = request.data["item_id"]
        action_type = request.data["action_type"]
        
        if action_type == "move":
            # Get clearings where player has warriors
            clearings = Clearing.objects.filter(game_id=game_id)
            origin_options = []
            for c in clearings:
                if player_has_warriors_in_clearing(player, c):
                    origin_options.append({
                        "value": str(c.clearing_number),
                        "label": f"Clearing {c.clearing_number} ({c.get_suit_display()})"
                    })
            
            return self.generate_step(
                name="pick-origin",
                prompt="Select origin clearing",
                endpoint="pick-origin",
                payload_details=[{"type": "clearing", "name": "origin_number"}],
                accumulated_payload={"item_id": item_id, "action_type": action_type},
                options=origin_options,
                faction=Faction(player.faction)
            )
        else:
            # Battle
            clearings = Clearing.objects.filter(game_id=game_id)
            battle_options = []
            for c in clearings:
                if player_has_warriors_in_clearing(player, c):
                    # Check for enemy pieces
                    from game.queries.general import get_enemy_factions_in_clearing
                    enemies = get_enemy_factions_in_clearing(player, c)
                    if enemies:
                        battle_options.append({
                            "value": str(c.clearing_number),
                            "label": f"Clearing {c.clearing_number} ({c.get_suit_display()})"
                        })
            
            return self.generate_step(
                name="pick-clearing",
                prompt="Select clearing for battle",
                endpoint="pick-clearing",
                payload_details=[{"type": "clearing", "name": "clearing_number"}],
                accumulated_payload={"item_id": item_id, "action_type": action_type},
                options=battle_options,
                faction=Faction(player.faction)
            )

    # MOVE FLOW
    def post_pick_origin(self, request, game_id):
        player = self.player_by_request(request, game_id)
        origin_number = request.data["origin_number"]
        origin = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=origin_number)
        
        # Get adjacent clearings where player controls either origin or destination
        from game.queries.general import determine_clearing_rule
        adjacents = origin.connected_clearings.all()
        dest_options = []
        origin_rule = determine_clearing_rule(origin)
        
        for dest in adjacents:
            dest_rule = determine_clearing_rule(dest)
            # determine_clearing_rule returns Player or None
            origin_ruler_faction = Faction(origin_rule.faction) if origin_rule else None
            dest_ruler_faction = Faction(dest_rule.faction) if dest_rule else None
            
            if origin_ruler_faction == Faction(player.faction) or dest_ruler_faction == Faction(player.faction):
                dest_options.append({
                    "value": str(dest.clearing_number),
                    "label": f"Clearing {dest.clearing_number} ({dest.get_suit_display()})"
                })
        
        return self.generate_step(
            name="pick-destination",
            prompt="Select destination clearing",
            endpoint="pick-destination",
            payload_details=[{"type": "clearing", "name": "destination_number"}],
            accumulated_payload={**request.data},
            options=dest_options,
            faction=Faction(player.faction)
        )

    def post_pick_destination(self, request, game_id):
        player = self.player_by_request(request, game_id)
        origin_number = request.data["origin_number"]
        origin = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=origin_number)
        count = warrior_count_in_clearing(player, origin)
        
        options = [{"value": str(i), "label": str(i)} for i in range(1, count + 1)]
        
        return self.generate_step(
            name="pick-count",
            prompt="Select number of warriors to move",
            endpoint="pick-count",
            payload_details=[{"type": "number", "name": "count"}],
            accumulated_payload={**request.data},
            options=options,
            faction=Faction(player.faction)
        )

    def post_pick_count(self, request, game_id):
        player = self.player_by_request(request, game_id)
        item_id = request.data["item_id"]
        origin_number = request.data["origin_number"]
        destination_number = request.data["destination_number"]
        count = int(request.data["count"])
        
        from game.models.game_models import CraftedCardEntry
        from game.game_data.cards.exiles_and_partisans import CardsEP
        
        card_entry = get_object_or_404(CraftedCardEntry, player=player, card__card_type=CardsEP.LEAGUE_OF_ADVENTURERS.name)
        item_entry = get_object_or_404(CraftedItemEntry, pk=item_id)
        origin = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=origin_number)
        destination = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=destination_number)
        
        move_data = {
            "origin_clearing": origin,
            "target_clearing": destination,
            "number": count
        }
        
        try:
            use_league_of_adventurers(card_entry, item_entry, move_data=move_data)
        except ValueError as e:
             raise ValidationError({"detail": str(e)})
             
        return self.generate_completed_step()

    # BATTLE FLOW
    def post_pick_clearing(self, request, game_id):
        player = self.player_by_request(request, game_id)
        clearing_number = request.data["clearing_number"]
        clearing = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=clearing_number)
        
        from game.queries.general import get_enemy_factions_in_clearing
        enemies = get_enemy_factions_in_clearing(player, clearing)
        opponent_options = []
        for enemy_faction in enemies:
             opponent_options.append({
                 "value": enemy_faction.value,
                 "label": enemy_faction.label
             })
             
        return self.generate_step(
            name="pick-opponent",
            prompt="Select opponent to battle",
            endpoint="pick-opponent",
            payload_details=[{"type": "faction", "name": "opponent_faction"}],
            accumulated_payload={**request.data},
            options=opponent_options,
            faction=Faction(player.faction)
        )

    def post_pick_opponent(self, request, game_id):
        player = self.player_by_request(request, game_id)
        item_id = request.data["item_id"]
        clearing_number = request.data["clearing_number"]
        opponent_faction_code = request.data["opponent_faction"]
        
        from game.models.game_models import CraftedCardEntry
        from game.game_data.cards.exiles_and_partisans import CardsEP
        
        card_entry = get_object_or_404(CraftedCardEntry, player=player, card__card_type=CardsEP.LEAGUE_OF_ADVENTURERS.name)
        item_entry = get_object_or_404(CraftedItemEntry, pk=item_id)
        clearing = get_object_or_404(Clearing, game=self.game(game_id), clearing_number=clearing_number)
        
        battle_data = {
            "clearing": clearing,
            "opponent_faction": opponent_faction_code
        }
        
        try:
            use_league_of_adventurers(card_entry, item_entry, battle_data=battle_data)
        except ValueError as e:
             raise ValidationError({"detail": str(e)})
             
        return self.generate_completed_step()
