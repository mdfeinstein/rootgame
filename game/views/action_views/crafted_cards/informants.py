from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from game.views.action_views.general import GameActionView
from game.models.game_models import CraftedCardEntry, DiscardPileEntry, Faction
from game.models.events.crafted_cards import InformantsEvent
from game.transactions.crafted_cards.informants import use_informants, skip_informants
from game.game_data.cards.exiles_and_partisans import CardsEP

class InformantsView(GameActionView):
    def get(self, request, *args, **kwargs):
        game_id = request.query_params.get("game_id")
        player = self.player_by_request(request, game_id)
        
        event_entry = InformantsEvent.objects.filter(
            event__game_id=game_id, 
            event__is_resolved=False, 
            crafted_card_entry__player=player
        ).first()
        
        if not event_entry:
            raise ValidationError({"detail": "No active Informants event for player."})
            
        card_entry = event_entry.crafted_card_entry
        
        options = [
            {"value": "use", "label": "Use Informants"},
            {"value": "skip", "label": "Skip"}
        ]
        
        self.faction = Faction(player.faction)
        self.first_step = {
            "faction": self.faction.label,
            "name": "use-or-skip",
            "prompt": "Do you want to use Informants to take an ambush card from the discard pile?",
            "endpoint": "use-or-skip",
            "payload_details": [{"type": "choice", "name": "choice"}],
            "options": options,
            "accumulated_payload": {"card_entry_id": card_entry.id}
        }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "use-or-skip":
                return self.post_use_or_skip(request, game_id)
            case "pick-ambush-card":
                return self.post_pick_ambush_card(request, game_id)
            case _:
                return Response(status=status.HTTP_404_NOT_FOUND)

    def post_use_or_skip(self, request, game_id):
        player = self.player_by_request(request, game_id)
        choice = request.data["choice"]
        card_entry_id = request.data["card_entry_id"]
        card_entry = get_object_or_404(CraftedCardEntry, id=card_entry_id, player=player)

        if choice == "skip":
            skip_informants(card_entry)
            return self.generate_completed_step()
        
        # Choice is "use"
        # Check if there are any ambush cards in discard pile
        ambush_entries = DiscardPileEntry.objects.filter(game_id=game_id)
        options = []
        for entry in ambush_entries:
            card_data = CardsEP[entry.card.card_type].value
            if card_data.ambush:
                options.append({
                    "value": str(entry.id),
                    "label": f"{card_data.title} ({card_data.suit.name})"
                })
        
        if not options:
            raise ValidationError({"detail": "No ambush cards available in the discard pile."})

        return self.generate_step(
            name="pick-ambush-card",
            prompt="Pick an ambush card from the discard pile",
            endpoint="pick-ambush-card",
            payload_details=[{"type": "discard_card", "name": "discard_entry_id"}],
            accumulated_payload={"card_entry_id": card_entry_id},
            options=options,
            faction=Faction(player.faction)
        )

    def post_pick_ambush_card(self, request, game_id):
        player = self.player_by_request(request, game_id)
        card_entry_id = request.data["card_entry_id"]
        discard_entry_id = request.data["discard_entry_id"]
        
        card_entry = get_object_or_404(CraftedCardEntry, id=card_entry_id, player=player)
        discard_entry = get_object_or_404(DiscardPileEntry, id=discard_entry_id, game_id=game_id)
        
        use_informants(card_entry, discard_entry)
        
        return self.generate_completed_step()
