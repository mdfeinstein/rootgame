from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import Faction, Player, Clearing
from game.models.events.crafted_cards import EyrieEmigreEvent
from game.models.events.event import EventType
from game.queries.current_action.events import get_current_event
from game.transactions.crafted_cards.eyrie_emigre import (
    emigre_move,
    emigre_battle,
    emigre_skip,
    emigre_skip_battle
)
from game.queries.general import validate_has_legal_moves, validate_legal_move, get_enemy_factions_in_clearing
from game.decorators.transaction_decorator import atomic_game_action

class EyrieEmigreView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = kwargs.get("game_id") or request.query_params.get("game_id")
        player = self.player(request, game_id)
        event = self.get_event(game_id)

        if not event.move_completed:
            # Step 1: Use or Skip
            options = [
                {"value": "use", "label": "Use Eyrie Emigre"},
                {"value": "skip", "label": "Skip"}
            ]
            return self.generate_step(
                name="use-or-skip",
                prompt="Do you want to use Eyrie Emigre to move and battle?",
                endpoint="use-or-skip",
                payload_details=[{"type": "choice", "name": "choice"}],
                options=options,
                faction=Faction(player.faction)
            )
        else:
            # Step 3: Battle or Skip Battle
            return self.get_battle_step(event, player)

    def route_post(self, request, game_id: int, route: str, *args, **kwargs):
        player = self.player(request, game_id)
        self.faction = Faction(player.faction)
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
                raise ValidationError("Invalid route")

    def post_use_or_skip(self, request, game_id):
        player = self.player(request, game_id)
        choice = request.data["choice"]
        event = self.get_event(game_id)
        
        if choice == "skip":
            try:
                atomic_game_action(emigre_skip)(event)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        
        # Choice is "use" -> Start move flow
        return self.generate_step(
            name="origin",
            prompt="Select origin clearing for Eyrie Emigre move",
            endpoint="origin",
            payload_details=[{"type": "clearing_number", "name": "origin_clearing"}],
            faction=Faction(player.faction)
        )

    def post_origin(self, request, game_id):
        player = self.player(request, game_id)
        clearing_number = int(request.data["origin_clearing"])
        
        try:
            clearing = Clearing.objects.get(game_id=game_id, clearing_number=clearing_number)
            validate_has_legal_moves(player, clearing)
        except Clearing.DoesNotExist:
             raise ValidationError({"detail": "Clearing not found"})
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        return self.generate_step(
            name="destination",
            prompt="Select destination clearing",
            endpoint="destination",
            payload_details=[{"type": "clearing_number", "name": "destination_clearing"}],
            accumulated_payload={"origin_clearing": clearing_number},
            faction=Faction(player.faction)
        )

    def post_destination(self, request, game_id):
        player = self.player(request, game_id)
        origin_clearing_number = int(request.data["origin_clearing"])
        destination_clearing_number = int(request.data["destination_clearing"])

        try:
            origin_clearing = Clearing.objects.get(game_id=game_id, clearing_number=origin_clearing_number)
            destination_clearing = Clearing.objects.get(game_id=game_id, clearing_number=destination_clearing_number)
            validate_legal_move(player, origin_clearing, destination_clearing)
        except Clearing.DoesNotExist:
             raise ValidationError({"detail": "Clearing not found"})
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        return self.generate_step(
            name="count",
            prompt="Select number of warriors to move",
            endpoint="count",
            payload_details=[{"type": "number", "name": "count"}],
            accumulated_payload={
                "origin_clearing": origin_clearing_number,
                "destination_clearing": destination_clearing_number
            },
            faction=Faction(player.faction)
        )

    def post_count(self, request, game_id):
        player = self.player(request, game_id)
        origin_clearing_number = int(request.data["origin_clearing"])
        destination_clearing_number = int(request.data["destination_clearing"])
        count = int(request.data["count"])
        event = self.get_event(game_id)
        
        try:
            origin_clearing = Clearing.objects.get(game_id=game_id, clearing_number=origin_clearing_number)
            destination_clearing = Clearing.objects.get(game_id=game_id, clearing_number=destination_clearing_number)
        except Clearing.DoesNotExist:
             raise ValidationError({"detail": "Clearing not found"})

        try:
            atomic_game_action(emigre_move)(event, origin_clearing, destination_clearing, count)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        try:
            event.refresh_from_db()
        except EyrieEmigreEvent.DoesNotExist:
            # Event was deleted due to failure (no enemies in destination)
            return self.generate_completed_step()

        if event.event.is_resolved:
            return self.generate_completed_step()

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
            options=options,
            faction=Faction(player.faction)
        )

    def post_battle_choice(self, request, game_id):
        player = self.player(request, game_id)
        choice = request.data["choice"]
        event = self.get_event(game_id)

        if choice == "skip":
            try:
                atomic_game_action(emigre_skip_battle)(event)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        # Choice is "battle" -> Show enemy factions
        enemy_factions = get_enemy_factions_in_clearing(player, event.move_destination)
        options = [{"value": f.value, "label": f.label} for f in enemy_factions]

        return self.generate_step(
            name="battle",
            prompt="Select faction to battle",
            endpoint="battle",
            payload_details=[{"type": "faction", "name": "faction_name"}],
            options=options,
            faction=Faction(player.faction)
        )

    def post_battle(self, request, game_id):
        player = self.player(request, game_id)
        faction_name = request.data["faction_name"]
        event = self.get_event(game_id)
        
        target_faction = Faction(faction_name)

        try:
            atomic_game_action(emigre_battle)(event, target_faction)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        return self.generate_completed_step()

    def get_event(self, game_id: int):
        event = get_current_event(self.game(game_id))
        try:
            return EyrieEmigreEvent.objects.get(event=event)
        except EyrieEmigreEvent.DoesNotExist:
             raise ValidationError({"detail": "Current Event not Eyrie Emigre"})

    def player(self, request, game_id: int) -> Player:
        event_entry = self.get_event(game_id)
        return event_entry.crafted_card_entry.player
    
    def validate_timing(self, request, game_id: int, route: str, *args, **kwargs):
        event = get_current_event(self.game(game_id))
        if not event or event.type != EventType.EYRIE_EMIGRE:
            raise ValidationError({"detail": "Current Event not Eyrie Emigre"})
    
    def validate_player(self, request, game_id: int, route: str, *args, **kwargs):
        player = self.player(request, game_id)
        if player != self.player_by_request(request, game_id):
            raise ValidationError({"detail": "Not your turn"})
