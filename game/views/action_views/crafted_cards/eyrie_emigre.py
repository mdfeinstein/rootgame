from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import Faction, Player, Clearing
from game.models.events.crafted_cards import EyrieEmigreEvent
from game.transactions.crafted_cards.eyrie_emigre import (
    emigre_move,
    emigre_battle,
    emigre_skip,
    emigre_skip_battle
)
from game.queries.general import validate_has_legal_moves, validate_legal_move, get_enemy_factions_in_clearing

class EyrieEmigreView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = request.query_params.get("game_id")
        player = self.player_by_request(request, game_id)
        self.faction = Faction(player.faction)

        event = EyrieEmigreEvent.objects.filter(
            event__game_id=game_id, 
            event__is_resolved=False, 
            crafted_card_entry__player=player
        ).first()

        if not event:
            raise ValidationError({"detail": "No active Eyrie Emigre event for player."})

        if not event.move_completed:
            # Step 1: Use or Skip
            options = [
                {"value": "use", "label": "Use Eyrie Emigre"},
                {"value": "skip", "label": "Skip"}
            ]
            self.first_step = {
                "faction": self.faction.label,
                "name": "use-or-skip",
                "prompt": "Do you want to use Eyrie Emigre to move and battle?",
                "endpoint": "use-or-skip",
                "payload_details": [{"type": "choice", "name": "choice"}],
                "options": options,
                "accumulated_payload": {"event_id": event.id}
            }
        else:
            # Step 3: Battle or Skip Battle
            # This case handles if the player refreshing the page after moving but before battling
            return self.get_battle_step(event, player)

        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "use-or-skip":
                return self.post_use_or_skip(request, game_id)
            case "origin":
                return self.post_origin(request, game_id)
            case "destination":
                return self.post_destination(request, game_id)
            case "count":
                return self.post_count(request, game_id)
            case "battle-choice":
                return self.post_battle_choice(request, game_id)
            case "battle":
                return self.post_battle(request, game_id)
            case _:
                return Response(status=status.HTTP_404_NOT_FOUND)

    def post_use_or_skip(self, request, game_id):
        player = self.player_by_request(request, game_id)
        choice = request.data["choice"]
        event_id = request.data["event_id"]
        event = get_object_or_404(EyrieEmigreEvent, id=event_id, crafted_card_entry__player=player)

        if choice == "skip":
            emigre_skip(event)
            return self.generate_completed_step()
        
        # Choice is "use" -> Start move flow
        return self.generate_step(
            name="origin",
            prompt="Select origin clearing for Eyrie Emigre move",
            endpoint="origin",
            payload_details=[{"type": "clearing_number", "name": "origin_clearing"}],
            accumulated_payload={"event_id": event.id},
            faction=Faction(player.faction)
        )

    def post_origin(self, request, game_id):
        player = self.player_by_request(request, game_id)
        event_id = request.data["event_id"]
        clearing_number = int(request.data["origin_clearing"])
        
        try:
            clearing = Clearing.objects.get(game_id=game_id, clearing_number=clearing_number)
            validate_has_legal_moves(player, clearing)
        except (Clearing.DoesNotExist, ValueError) as e:
            raise ValidationError({"detail": str(e)})

        return self.generate_step(
            name="destination",
            prompt="Select destination clearing",
            endpoint="destination",
            payload_details=[{"type": "clearing_number", "name": "destination_clearing"}],
            accumulated_payload={"event_id": event_id, "origin_clearing": clearing_number},
            faction=Faction(player.faction)
        )

    def post_destination(self, request, game_id):
        player = self.player_by_request(request, game_id)
        event_id = request.data["event_id"]
        origin_clearing_number = int(request.data["origin_clearing"])
        destination_clearing_number = int(request.data["destination_clearing"])

        try:
            origin_clearing = Clearing.objects.get(game_id=game_id, clearing_number=origin_clearing_number)
            destination_clearing = Clearing.objects.get(game_id=game_id, clearing_number=destination_clearing_number)
            validate_legal_move(player, origin_clearing, destination_clearing)
        except (Clearing.DoesNotExist, ValueError) as e:
            raise ValidationError({"detail": str(e)})

        return self.generate_step(
            name="count",
            prompt="Select number of warriors to move",
            endpoint="count",
            payload_details=[{"type": "number", "name": "count"}],
            accumulated_payload={
                "event_id": event_id, 
                "origin_clearing": origin_clearing_number,
                "destination_clearing": destination_clearing_number
            },
            faction=Faction(player.faction)
        )

    def post_count(self, request, game_id):
        player = self.player_by_request(request, game_id)
        event_id = request.data["event_id"]
        origin_clearing_number = int(request.data["origin_clearing"])
        destination_clearing_number = int(request.data["destination_clearing"])
        count = int(request.data["count"])

        event = get_object_or_404(EyrieEmigreEvent, id=event_id, crafted_card_entry__player=player)
        origin_clearing = get_object_or_404(Clearing, game_id=game_id, clearing_number=origin_clearing_number)
        destination_clearing = get_object_or_404(Clearing, game_id=game_id, clearing_number=destination_clearing_number)

        try:
            emigre_move(event, origin_clearing, destination_clearing, count)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        # Re-fetch event to see if it was resolved (due to failure/no enemies)
        event.refresh_from_db()
        if event.event.is_resolved:
            return self.generate_completed_step()

        # If move successful and enemies present, offer battle
        return self.get_battle_step(event, player)

    def get_battle_step(self, event, player):
        options = [
            {"value": "battle", "label": "Battle"},
            {"value": "skip", "label": "Skip (Discards Card)"}
        ]
        return self.generate_step(
            name="battle-choice",
            prompt=f"Do you want to battle in clearing {event.move_destination.clearing_number}?",
            endpoint="battle-choice",
            payload_details=[{"type": "choice", "name": "choice"}],
            accumulated_payload={"event_id": event.id},
            options=options,
            faction=Faction(player.faction)
        )

    def post_battle_choice(self, request, game_id):
        player = self.player_by_request(request, game_id)
        choice = request.data["choice"]
        event_id = request.data["event_id"]
        event = get_object_or_404(EyrieEmigreEvent, id=event_id, crafted_card_entry__player=player)

        if choice == "skip":
            emigre_skip_battle(event)
            return self.generate_completed_step()

        # Choice is "battle" -> Show enemy factions
        enemy_factions = get_enemy_factions_in_clearing(player, event.move_destination)
        options = [{"value": f.name, "label": f.label} for f in enemy_factions]

        return self.generate_step(
            name="battle",
            prompt="Select faction to battle",
            endpoint="battle",
            payload_details=[{"type": "faction", "name": "faction"}],
            accumulated_payload={"event_id": event_id},
            options=options,
            faction=Faction(player.faction)
        )

    def post_battle(self, request, game_id):
        player = self.player_by_request(request, game_id)
        event_id = request.data["event_id"]
        target_faction_name = request.data["faction"]
        
        event = get_object_or_404(EyrieEmigreEvent, id=event_id, crafted_card_entry__player=player)
        target_faction = Faction[target_faction_name]

        try:
            emigre_battle(event, target_faction)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        return self.generate_completed_step()
