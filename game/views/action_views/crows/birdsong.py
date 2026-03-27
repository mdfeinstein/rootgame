from game.models.events import Event, EventType
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from game.models.game_models import Clearing, Faction, Suit
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowBirdsong
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.decorators.transaction_decorator import atomic_game_action
from game.views.action_views.general import GameActionView
from game.queries.crows.turn import validate_step
from game.queries.crows.crafting import (
    is_able_to_be_crafted,
    validate_crafting_pieces_satisfy_requirements,
)
from game.transactions.crows.birdsong import (
    crows_craft_card,
    end_craft_step,
    flip_plot,
    end_flip_step,
    crows_recruit,
    manual_recruit,
    end_recruit_step,
)


class CrowsCraftingView(GameActionView):
    action_name = "CROWS_CRAFTING"
    faction = Faction.CROWS

    first_step = {
        "faction": faction.label,
        "name": "select_card",
        "prompt": "Select a card to craft or choose nothing to end crafting.",
        "endpoint": "card",
        "payload_details": [{"type": "card", "name": "card_to_craft"}],
        "options": [
            {
                "value": "",
                "label": "Done Crafting",
                "info": "Finish crafting cards this turn.",
            },
        ],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "card":
            return self.post_card(request, game_id)
        elif route == "piece":
            return self.post_piece(request, game_id)
        else:
            raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_card(self, request, game_id: int):
        player = self.player(request, game_id)
        if request.data["card_to_craft"] == "":
            try:
                atomic_game_action(end_craft_step)(player)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        card = CardsEP[request.data["card_to_craft"]]
        if not is_able_to_be_crafted(player, card):
            raise ValidationError("Not enough plot tokens to craft this card")

        suits_needed = [cost.label for cost in card.value.cost]
        prompt = f"Select plot tokens (revealed or hidden) to craft this card. Needed: {suits_needed}."
        return self.generate_step(
            "select_pieces",
            prompt,
            "piece",
            [{"type": "clearing_number", "name": "plot_clearing_number"}],
            {
                "card_to_craft": request.data["card_to_craft"],
                "plot_clearing_numbers": [],
            },
        )

    def post_piece(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        card = CardsEP[request.data["card_to_craft"]]
        old_clearing_numbers = request.data["plot_clearing_numbers"]
        new_clearing_number = int(request.data["plot_clearing_number"])
        clearing_numbers = old_clearing_numbers + [new_clearing_number]

        try:
            plots = [
                PlotToken.objects.get(player=player, clearing__clearing_number=c_num)
                for c_num in clearing_numbers
            ]
        except PlotToken.DoesNotExist:
            raise ValidationError(
                {"detail": "Plot token not found in one or more selected clearings"}
            )

        try:
            all_pieces_satisfied = validate_crafting_pieces_satisfy_requirements(
                player, card, plots
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        if all_pieces_satisfied:
            # try to craft
            try:
                atomic_game_action(crows_craft_card)(player, card, plots)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        # otherwise, continue to select pieces
        suits_needed = [cost.label for cost in card.value.cost]
        suits_selected = [Suit(plot.clearing.suit).label for plot in plots]
        prompt = f"Select more crafting pieces. Needed: {suits_needed}. Selected: {suits_selected}"
        return self.generate_step(
            "select_pieces",
            prompt,
            "piece",
            [{"type": "clearing_number", "name": "plot_clearing_number"}],
            {
                "card_to_craft": request.data["card_to_craft"],
                "plot_clearing_numbers": clearing_numbers,
            },
        )

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, CrowBirdsong.CrowBirdsongSteps.CRAFT)


class CrowsFlippingView(GameActionView):
    action_name = "CROWS_FLIPPING"
    faction = Faction.CROWS

    first_step = {
        "faction": faction.label,
        "name": "select_plot_to_flip",
        "prompt": "Select a facedown plot token to flip face-up, or choose nothing to end flipping step.",
        "endpoint": "clearing",
        "payload_details": [{"type": "clearing_number", "name": "plot_clearing"}],
        "options": [
            {
                "value": "",
                "label": "Done Flipping",
                "info": "Finish flipping plot tokens face-up.",
            },
        ],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "clearing":
            return self.post_clearing(request, game_id)
        raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_clearing(self, request, game_id: int):
        player = self.player(request, game_id)
        if request.data["plot_clearing"] == "":
            try:
                atomic_game_action(end_flip_step)(player)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        clearing_number = int(request.data["plot_clearing"])
        try:
            token = PlotToken.objects.get(
                player=player,
                is_facedown=True,
                clearing__clearing_number=clearing_number,
            )
        except PlotToken.DoesNotExist:
            raise ValidationError(
                {"detail": "No facedown plot token found in this clearing."}
            )

        try:
            atomic_game_action(flip_plot)(player, token)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, CrowBirdsong.CrowBirdsongSteps.FLIP)


class CrowsRecruitingView(GameActionView):
    action_name = "CROWS_RECRUITING"
    faction = Faction.CROWS

    first_step = {
        "faction": faction.label,
        "name": "select_card_to_recruit",
        "prompt": "Select a card from your hand to recruit a warrior into every clearing matching its suit. If reserving runs out, you will manually pick clearings.",
        "endpoint": "card",
        "payload_details": [{"type": "card", "name": "card_used"}],
        "options": [
            {
                "value": "",
                "label": "Done Recruiting",
                "info": "Finish recruiting and proceed to the next step.",
            }
        ],
    }

    def route_post(self, request, game_id: int, route: str):
        if route == "card":
            return self.post_card(request, game_id)
        elif route == "bird_suit_selection":
            return self.post_bird_suit(request, game_id)
        raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_card(self, request, game_id: int):
        player = self.player(request, game_id)
        if request.data["card_used"] == "":
            try:
                atomic_game_action(end_recruit_step)(player)
            except ValueError as e:
                raise ValidationError({"detail": str(e)})
            return self.generate_completed_step()

        card = CardsEP[request.data["card_used"]]

        # If it's a bird card, prompt the user to select the suit they are activating as
        if Suit(card.value.suit) == Suit.WILD:
            return self.generate_step(
                "select_suit_for_bird_card",
                "Select a suit to recruit in using this Bird card.",
                "bird_suit_selection",
                [{"type": "suit", "name": "selected_suit"}],
                {"card_used": request.data["card_used"]},
                options=[
                    {"value": Suit.RED.name, "label": "Fox"},
                    {"value": Suit.ORANGE.name, "label": "Mouse"},
                    {"value": Suit.YELLOW.name, "label": "Rabbit"},
                ],
            )

        # Otherwise recruit directly
        try:
            atomic_game_action(crows_recruit)(player, card)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        return self.generate_completed_step()

    def post_bird_suit(self, request, game_id: int):
        player = self.player(request, game_id)
        card = CardsEP[request.data["card_used"]]
        suit_string = request.data["selected_suit"]
        if not suit_string:
            raise ValidationError("You must provide a chosen suit for a bird card")

        target_suit = Suit[suit_string]

        try:
            atomic_game_action(crows_recruit)(player, card, target_suit)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        validate_step(player, CrowBirdsong.CrowBirdsongSteps.RECRUIT)


class CrowsManualRecruitView(GameActionView):
    action_name = "CROWS_MANUAL_RECRUIT"
    faction = Faction.CROWS

    def get(self, request):
        game_id = int(request.query_params.get("game_id"))
        player = self.player_by_faction(request, game_id)

        from game.models.events.crows import CrowRecruitEvent
        from game.models.events.event import Event, EventType

        active_event = Event.objects.filter(
            game=self.game(game_id),
            type=EventType.CROW_RECRUIT,
            is_resolved=False,
        ).first()

        if not active_event:
            raise ValidationError("No active recruit event")

        recruit_event = CrowRecruitEvent.objects.get(event=active_event)

        self.first_step = {
            "faction": self.faction.label,
            "name": "select_clearing",
            "prompt": f"Not enough warriors to fill all {Suit(recruit_event.suit).label} clearings. Choose a clearing to recruit into.",
            "endpoint": "clearing",
            "payload_details": [{"type": "clearing_number", "name": "clearing_number"}],
        }
        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        if route == "clearing":
            return self.post_clearing(request, game_id)
        raise ValidationError("Invalid route", code=status.HTTP_404_NOT_FOUND)

    def post_clearing(self, request, game_id: int):
        player = self.player(request, game_id)
        clearing_number = int(request.data["clearing_number"])

        from game.models.game_models import Clearing

        try:
            clearing = Clearing.objects.get(
                game=self.game(game_id), clearing_number=clearing_number
            )
        except Clearing.DoesNotExist:
            raise ValidationError("Clearing not found")

        # grab the event again
        from game.models.events.event import Event, EventType

        active_event = Event.objects.filter(
            game=self.game(game_id),
            type=EventType.CROW_RECRUIT,
            is_resolved=False,
        ).first()

        if not active_event:
            raise ValidationError("No active recruit event")

        try:
            atomic_game_action(manual_recruit)(player, clearing, active_event)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        # check if it finished
        active_event.refresh_from_db()
        if active_event.is_resolved:
            return self.generate_completed_step()

        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        try:
            validate_step(player, CrowBirdsong.CrowBirdsongSteps.RECRUIT)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        try:
            event = Event.objects.get(
                game=self.game(game_id),
                type=EventType.CROW_RECRUIT,
                is_resolved=False,
            )
        except Event.DoesNotExist:
            raise ValidationError("No active recruit event")
