from rest_framework import status
from rest_framework.exceptions import ValidationError

from game.decorators.transaction_decorator import atomic_game_action
from game.errors import IllegalActionError, UnavailableActionError
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Faction
from game.models.moles.buildings import Citadel, Market
from game.models.moles.turn import MoleEvening
from game.queries.general import get_player_hand_size
from game.queries.moles.crafting import validate_crafting_pieces_satisfy_requirements
from game.queries.moles.evening import validate_discard_card
from game.queries.moles.turn import validate_step
from game.transactions.moles.evening import craft_card, discard_card, end_crafting, end_discard
from game.views.action_views.general import GameActionView


class MolesCraftingView(GameActionView):
    action_name = "MOLES_CRAFT"
    faction = Faction.MOLES

    first_step = {
        "faction": Faction.MOLES.label,
        "name": "select_card",
        "prompt": "Select a card to craft or Done to end crafting.",
        "endpoint": "card",
        "payload_details": [{"type": "card", "name": "card_to_craft"}],
        "options": [
            {"value": "", "label": "Done Crafting"},
        ],
    }

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        player = self.player(request, game_id)
        validate_step(player, MoleEvening.MoleEveningSteps.CRAFT)
        # Build options from player's hand
        self.first_step = dict(self.first_step)
        self.first_step["options"] = self._get_card_options(player)
        return super().get(request)

    def _get_card_options(self, player):
        """Get cards in hand as options."""
        from game.models.game_models import HandEntry
        cards = HandEntry.objects.filter(player=player).values_list("card__card_type", flat=True)
        options = []
        for card_type in cards:
            try:
                card_enum = CardsEP[card_type]
                options.append({
                    "value": card_enum.name,
                    "label": card_enum.value.title,
                })
            except KeyError:
                pass
        options.append({"value": "", "label": "Done Crafting"})
        return options

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "card":
                return self.post_card(request, game_id)
            case "building":
                return self.post_building(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_card(self, request, game_id: int):
        player = self.player(request, game_id)
        validate_step(player, MoleEvening.MoleEveningSteps.CRAFT)

        card_name = request.data.get("card_to_craft", "")
        if card_name == "":
            try:
                atomic_game_action(end_crafting)(player)
            except (IllegalActionError, UnavailableActionError) as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        try:
            card_enum = CardsEP[card_name]
        except KeyError:
            raise ValidationError(f"Invalid card: {card_name}")

        # Get crafting cost
        cost = card_enum.value.cost
        cost_labels = [c.label for c in cost]

        return self.generate_step(
            "select_building",
            f"Select {len(cost)} buildings to craft {card_enum.value.title}. Needed: {cost_labels}.",
            "building",
            [{"type": "building_id", "name": "building_id"}],
            accumulated_payload={"card_to_craft": card_name, "building_ids": []},
            options=self._get_building_options(player),
        )

    def _get_building_options(self, player):
        """Get available buildings for crafting."""
        options = []

        # Get citadels
        citadels = Citadel.objects.filter(
            player=player, building_slot__isnull=False, crafted_with=False
        )
        for building in citadels:
            clearing = building.building_slot.clearing
            suit = clearing.suit.label
            options.append({
                "value": str(building.id),
                "label": f"Citadel in clearing {clearing.clearing_number} ({suit})",
            })

        # Get markets
        markets = Market.objects.filter(
            player=player, building_slot__isnull=False, crafted_with=False
        )
        for building in markets:
            clearing = building.building_slot.clearing
            suit = clearing.suit.label
            options.append({
                "value": str(building.id),
                "label": f"Market in clearing {clearing.clearing_number} ({suit})",
            })

        options.append({"value": "", "label": "Back to card selection"})
        return options

    def post_building(self, request, game_id: int):
        player = self.player(request, game_id)
        validate_step(player, MoleEvening.MoleEveningSteps.CRAFT)

        card_name = request.data.get("card_to_craft", "")
        building_ids_str = request.data.get("building_ids", [])
        new_building_id = request.data.get("building_id", "")

        if not card_name:
            raise ValidationError("Card not set")

        try:
            card_enum = CardsEP[card_name]
        except KeyError:
            raise ValidationError(f"Invalid card: {card_name}")

        cost = card_enum.value.cost
        cost_labels = [c.label for c in cost]

        # If empty string, go back to card selection
        if new_building_id == "":
            return self.generate_step(
                "select_card",
                "Select a card to craft or Done to end crafting.",
                "card",
                [{"type": "card", "name": "card_to_craft"}],
                options=self._get_card_options(player),
            )

        # Add building to list
        try:
            building_ids = building_ids_str + [int(new_building_id)]
        except (ValueError, TypeError):
            raise ValidationError("Invalid building ID")

        # Fetch building objects
        try:
            buildings = []
            for bid in building_ids:
                citadel = Citadel.objects.filter(id=bid, player=player).first()
                market = Market.objects.filter(id=bid, player=player).first()
                b = citadel or market
                if not b:
                    raise ValidationError(f"Building {bid} not found")
                buildings.append(b)
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(str(e))

        # Check if requirements are satisfied
        try:
            all_satisfied = validate_crafting_pieces_satisfy_requirements(player, card_enum, buildings)
        except Exception as e:
            raise ValidationError(str(e))

        if all_satisfied:
            # Craft the card
            try:
                atomic_game_action(craft_card)(player, card_enum, buildings)
            except (IllegalActionError, UnavailableActionError) as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        # Continue selecting buildings
        selected_suits = [
            b.building_slot.clearing.suit.label for b in buildings
        ]
        prompt = f"Select more buildings. Needed: {cost_labels}. Selected so far: {selected_suits}."
        return self.generate_step(
            "select_building",
            prompt,
            "building",
            [{"type": "building_id", "name": "building_id"}],
            accumulated_payload={"card_to_craft": card_name, "building_ids": building_ids},
            options=self._get_building_options(player),
        )


class MolesDiscardView(GameActionView):
    action_name = "MOLES_DISCARD"
    faction = Faction.MOLES

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        player = self.player(request, game_id)
        validate_step(player, MoleEvening.MoleEveningSteps.DISCARD)

        hand_size = get_player_hand_size(player)
        if hand_size <= 5:
            # Auto-complete if no discards needed
            try:
                atomic_game_action(end_discard)(player)
            except (IllegalActionError, UnavailableActionError):
                pass
            return self.generate_completed_step()

        need_to_discard = hand_size - 5
        self.first_step = {
            "faction": Faction.MOLES.label,
            "name": "select_card",
            "prompt": f"Select {need_to_discard} cards to discard.",
            "endpoint": "card",
            "payload_details": [{"type": "card", "name": "card_to_discard"}],
            "options": self._get_card_options(player),
        }
        return super().get(request)

    def _get_card_options(self, player):
        """Get cards in hand as discard options."""
        from game.models.game_models import HandEntry
        cards = HandEntry.objects.filter(player=player)
        options = []
        for entry in cards:
            try:
                card_enum = CardsEP[entry.card.card_type]
                options.append({
                    "value": str(entry.id),
                    "label": card_enum.value.title,
                })
            except KeyError:
                pass
        return options

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "card":
                return self.post_card(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_card(self, request, game_id: int):
        player = self.player(request, game_id)
        validate_step(player, MoleEvening.MoleEveningSteps.DISCARD)

        from game.models.game_models import HandEntry

        card_entry_id = request.data.get("card_to_discard", "")
        if not card_entry_id:
            raise ValidationError("No card selected")

        try:
            card_entry = HandEntry.objects.get(id=int(card_entry_id), player=player)
        except (HandEntry.DoesNotExist, ValueError):
            raise ValidationError("Card not found in hand")

        try:
            atomic_game_action(discard_card)(player, card_entry)
        except (IllegalActionError, UnavailableActionError) as e:
            raise ValidationError({"detail": str(e)})

        # Check if we need to discard more
        hand_size = get_player_hand_size(player)
        if hand_size <= 5:
            try:
                atomic_game_action(end_discard)(player)
            except (IllegalActionError, UnavailableActionError):
                pass
            return self.generate_completed_step()

        need_to_discard = hand_size - 5
        return self.generate_step(
            "select_card",
            f"Select {need_to_discard} more cards to discard.",
            "card",
            [{"type": "card", "name": "card_to_discard"}],
            options=self._get_card_options(player),
        )
