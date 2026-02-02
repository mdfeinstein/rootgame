from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import CraftedCardEntry, DiscardPileEntry, Faction, Player
from game.models.events.crafted_cards import InformantsEvent
from game.models.events.event import EventType
from game.queries.current_action.events import get_current_event
from game.transactions.crafted_cards.informants import use_informants, skip_informants
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.decorators.transaction_decorator import atomic_game_action

class InformantsView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = kwargs.get("game_id") or request.query_params.get("game_id")
        player = self.player(request, game_id)
        
        event_entry = self.get_event(game_id)
            
        options = [
            {"value": "use", "label": "Use Informants"},
            {"value": "skip", "label": "Skip"}
        ]
        
        return self.generate_step(
            name="use-or-skip",
            prompt="Do you want to use Informants to take an ambush card from the discard pile?",
            endpoint="use-or-skip",
            payload_details=[{"type": "choice", "name": "choice"}],
            options=options,
            faction=Faction(player.faction)
        )

    def route_post(self, request, game_id: int, route: str, *args, **kwargs):
        player = self.player(request, game_id)
        self.faction = Faction(player.faction)
        match route:
            case "use-or-skip":
                return self.post_use_or_skip(request, game_id)
            case "pick-ambush-card":
                return self.post_pick_ambush_card(request, game_id)
            case _:
                raise ValidationError("Invalid route")

    def post_use_or_skip(self, request, game_id):
        player = self.player(request, game_id)
        choice = request.data["choice"]
        
        event_entry = self.get_event(game_id)
            
        card_entry = event_entry.crafted_card_entry

        if choice == "skip":
            try:
                atomic_game_action(skip_informants)(card_entry)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()
        
        # Choice is "use"
        # Check if there are any ambush cards in discard pile
        ambush_entries = DiscardPileEntry.objects.filter(game_id=game_id)
        options = []
        seen_cards = set()
        for entry in ambush_entries:
            card_type = entry.card.card_type
            card_data = CardsEP[card_type].value
            if card_data.ambush and card_type not in seen_cards:
                options.append({
                    "value": card_type,
                    "label": f"{card_data.title} ({card_data.suit.name})"
                })
                seen_cards.add(card_type)
        
        if not options:
            raise ValidationError({"detail": "No ambush cards available in the discard pile."})

        return self.generate_step(
            name="pick-ambush-card",
            prompt="Pick an ambush card from the discard pile",
            endpoint="pick-ambush-card",
            payload_details=[{"type": "card", "name": "card_name"}],
            options=options,
            faction=Faction(player.faction)
        )

    def post_pick_ambush_card(self, request, game_id):
        player = self.player(request, game_id)
        card_name = request.data["card_name"]
        
        event_entry = self.get_event(game_id)
            
        card_entry = event_entry.crafted_card_entry
        
        # Get one discard entry with this card name
        discard_entry = DiscardPileEntry.objects.filter(game_id=game_id, card__card_type=card_name).first()
        if not discard_entry:
            raise ValidationError("Card no longer in discard pile")
        
        try:
            atomic_game_action(use_informants)(card_entry, discard_entry)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        
        return self.generate_completed_step()

    def get_event(self, game_id: int):
        event = get_current_event(self.game(game_id))
        try:
            return InformantsEvent.objects.get(event=event)
        except InformantsEvent.DoesNotExist:
            raise ValidationError({"detail": "Current Event not Informants"})

    def player(self, request, game_id: int) -> Player:
        event_entry = self.get_event(game_id)
        return event_entry.crafted_card_entry.player
    
    def validate_timing(self, request, game_id: int, route: str, *args, **kwargs):
        event = get_current_event(self.game(game_id))
        if not event or event.type != EventType.INFORMANTS:
            raise ValidationError({"detail": "Current Event not Informants"})
    
    def validate_player(self, request, game_id: int, route: str, *args, **kwargs):
        player = self.player(request, game_id)
        if player != self.player_by_request(request, game_id):
            raise ValidationError({"detail": "Not your turn"})
