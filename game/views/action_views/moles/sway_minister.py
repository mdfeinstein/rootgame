from rest_framework.exceptions import ValidationError
from rest_framework import status

from game.models.game_models import Faction, HandEntry
from game.models.moles.turn import MoleDaylight
from game.models.moles.ministers import Minister
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.moles.turn import validate_step
from game.queries.moles.daylight import (
    validate_can_sway_minister,
    validate_card_in_hand,
    validate_cards_match_clearings,
)
from game.transactions.moles.daylight.sway_minister import sway_minister
from game.decorators.transaction_decorator import atomic_game_action
from game.views.action_views.general import GameActionView


class MolesSwayMinisterView(GameActionView):
    action_name = "MOLES_SWAY_MINISTER"
    faction = Faction.MOLES
    first_step = {
        "faction": Faction.MOLES.label,
        "name": "select_minister",
        "prompt": "Select a minister to sway.",
        "endpoint": "minister",
        "payload_details": [{"type": "minister_name", "name": "minister"}],
        "options": [],
    }

    def get_available_ministers(self, player):
        """Get list of swayable ministers with their crown requirements."""
        from game.models.moles.crown import Crown

        available = []
        required_cards_map = {"squire": 2, "noble": 3, "lord": 4}
        hand_size = HandEntry.objects.filter(player=player).count()

        for minister in Minister.objects.filter(player=player, swayed=False):
            crown_type = minister.crown_type
            cost = required_cards_map.get(crown_type, 0)

            # Check if player has enough cards for this minister's cost
            if hand_size < cost:
                continue

            # Check if a crown of this type is available
            crown_available = Crown.objects.filter(
                player=player, type=crown_type, used=False
            ).exists()

            if crown_available:
                available.append(
                    {
                        "value": minister.name,
                        "label": f"{minister.get_name_display()} ({cost} cards)",
                        "info": f"Crown: {crown_type.capitalize()}",
                    }
                )
        return available

    def get(self, request):
        player = self.player(request, int(request.GET.get("game_id")))
        validate_step(player, MoleDaylight.MoleDaylightSteps.SWAY_MINISTER)

        self.first_step = dict(self.first_step)
        self.first_step["options"] = self.get_available_ministers(player)
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "minister":
                return self.post_minister(request, game_id)
            case "card":
                return self.post_card(request, game_id)
            case "confirm":
                return self.post_confirm(request, game_id)
            case _:
                raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_minister(self, request, game_id: int):
        player = self.player(request, game_id)
        validate_step(player, MoleDaylight.MoleDaylightSteps.SWAY_MINISTER)

        minister_name_str = request.data.get("minister", "")
        if not minister_name_str:
            raise ValidationError("Minister is required", code=status.HTTP_400_BAD_REQUEST)

        try:
            minister_enum = Minister.MinisterName(minister_name_str)
        except ValueError:
            raise ValidationError(f"Invalid minister: {minister_name_str}")

        validate_can_sway_minister(player, minister_enum)

        # Move to card selection
        required_cards_map = {"squire": 2, "noble": 3, "lord": 4}
        minister_obj = Minister.objects.get(player=player, name=minister_enum)
        required_cards = required_cards_map.get(minister_obj.crown_type, 0)

        return self.generate_step(
            "select_card",
            f"Select {required_cards} cards to sway {minister_obj.get_name_display()}.",
            "card",
            [{"type": "card_name", "name": "card"}],
            accumulated_payload={"minister": minister_name_str, "cards": []},
            options=self.get_card_options(player, []),
        )

    def get_card_options(self, player, selected_cards: list[str]):
        """Get available cards for selection, filtered by what's possible given selections."""
        cards_in_hand = HandEntry.objects.filter(player=player).values_list(
            "card__card_type", flat=True
        )

        available = []
        for card_type in cards_in_hand:
            try:
                card_enum = CardsEP[card_type]
                available.append(
                    {
                        "value": card_enum.name,
                        "label": card_enum.value.title,
                    }
                )
            except KeyError:
                pass

        # Add Done option
        available.append({"value": "", "label": "Done selecting cards"})
        return available

    def post_card(self, request, game_id: int):
        player = self.player(request, game_id)
        validate_step(player, MoleDaylight.MoleDaylightSteps.SWAY_MINISTER)

        minister_name_str = request.data.get("minister", "")
        selected_cards_str = request.data.get("cards", [])

        if not minister_name_str:
            raise ValidationError("Minister not set")

        try:
            minister_enum = Minister.MinisterName(minister_name_str)
        except ValueError:
            raise ValidationError(f"Invalid minister: {minister_name_str}")

        minister_obj = Minister.objects.get(player=player, name=minister_enum)
        required_cards_map = {"squire": 2, "noble": 3, "lord": 4}
        required_cards = required_cards_map.get(minister_obj.crown_type, 0)

        card_name = request.data.get("card", "")
        accumulated = {"minister": minister_name_str, "cards": selected_cards_str}

        # If empty string, move to confirm if we have enough cards
        if card_name == "":
            if len(selected_cards_str) == required_cards:
                return self.generate_step(
                    "confirm",
                    f"Confirm swaying {minister_obj.get_name_display()} with {required_cards} cards.",
                    "confirm",
                    [{"type": "confirmed", "name": "confirmed"}],
                    accumulated_payload=accumulated,
                    options=[
                        {"value": "yes", "label": "Confirm"},
                        {"value": "no", "label": "Back to card selection"},
                    ],
                )
            else:
                raise ValidationError(
                    f"Need {required_cards - len(selected_cards_str)} more cards"
                )

        # Validate card is in hand
        try:
            card_enum = CardsEP[card_name]
        except KeyError:
            raise ValidationError(f"Invalid card: {card_name}")

        validate_card_in_hand(player, card_enum)

        # Validate card can be added (matches clearing with pieces, no duplicates)
        new_cards_list = selected_cards_str + [card_enum.name]
        try:
            cards_enums = [CardsEP[c] for c in new_cards_list]
            validate_cards_match_clearings(player, cards_enums)
        except Exception as e:
            raise ValidationError(str(e))

        # Add card to accumulated and show next options
        accumulated["cards"] = new_cards_list

        if len(new_cards_list) == required_cards:
            # Ready to confirm
            return self.generate_step(
                "confirm",
                f"Confirm swaying {minister_obj.get_name_display()} with {required_cards} cards.",
                "confirm",
                [{"type": "confirmed", "name": "confirmed"}],
                accumulated_payload=accumulated,
                options=[
                    {"value": "yes", "label": "Confirm"},
                    {"value": "no", "label": "Back to card selection"},
                ],
            )
        else:
            # Continue selecting
            selected_display = [CardsEP[c].value.title for c in new_cards_list]
            return self.generate_step(
                "select_card",
                f"Selected: {', '.join(selected_display)}. Select {required_cards - len(new_cards_list)} more cards.",
                "card",
                [{"type": "card_name", "name": "card"}],
                accumulated_payload=accumulated,
                options=self.get_card_options(player, new_cards_list),
            )

    def post_confirm(self, request, game_id: int):
        player = self.player(request, game_id)
        validate_step(player, MoleDaylight.MoleDaylightSteps.SWAY_MINISTER)

        minister_name_str = request.data.get("minister", "")
        selected_cards_str = request.data.get("cards", [])
        confirmed = request.data.get("confirmed", "")

        if not minister_name_str or not selected_cards_str:
            raise ValidationError("Missing minister or cards")

        accumulated = {"minister": minister_name_str, "cards": selected_cards_str}

        if confirmed != "yes":
            # Back to card selection
            try:
                minister_enum = Minister.MinisterName(minister_name_str)
            except ValueError:
                raise ValidationError(f"Invalid minister: {minister_name_str}")

            minister_obj = Minister.objects.get(player=player, name=minister_enum)
            required_cards_map = {"squire": 2, "noble": 3, "lord": 4}
            required_cards = required_cards_map.get(minister_obj.crown_type, 0)

            return self.generate_step(
                "select_card",
                f"Select {required_cards} cards to sway {minister_obj.get_name_display()}.",
                "card",
                [{"type": "card_name", "name": "card"}],
                accumulated_payload=accumulated,
                options=self.get_card_options(player, selected_cards_str),
            )

        # Execute sway_minister transaction
        try:
            minister_enum = Minister.MinisterName(minister_name_str)
            cards_enums = [CardsEP[c] for c in selected_cards_str]
            atomic_game_action(sway_minister)(player, minister_enum, cards_enums)
        except Exception as e:
            raise ValidationError(f"Failed to sway minister: {str(e)}")

        return self.generate_completed_step()
