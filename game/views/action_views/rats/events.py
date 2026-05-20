from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from game.decorators.transaction_decorator import atomic_game_action
from game.models.enums import ItemTypes
from game.models.events.rats import HoardTooFullEvent, LootingEvent, ResolveBitterEvent
from game.models.game_models import CraftedItemEntry, Faction, Item
from game.models.rats.player import CommandItemEntry, ProwessItemEntry
from game.queries.rats.pieces import get_warlord
from game.models.rats.tokens import Mob
from game.models.game_models import Clearing
from game.transactions.rats.bitter import absorb_mob, end_bitter
from game.transactions.rats.hoard import discard_hoard_item
from game.transactions.rats.looting import choose_loot
from game.views.action_views.general import GameActionView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ITEM_LABELS: dict[str, str] = {
    ItemTypes.BOOTS: "Boots",
    ItemTypes.BAG: "Bag",
    ItemTypes.COIN: "Coin",
    ItemTypes.HAMMER: "Hammer",
    ItemTypes.TEA: "Tea",
    ItemTypes.SWORD: "Sword",
    ItemTypes.CROSSBOW: "Crossbow",
}


def _item_label(item: Item) -> str:
    return _ITEM_LABELS.get(item.item_type, item.item_type)


def _get_active_hoard_event(player) -> HoardTooFullEvent | None:
    return (
        HoardTooFullEvent.objects.filter(player=player, event__is_resolved=False)
        .select_related("event")
        .first()
    )


def _get_active_bitter_event(player) -> ResolveBitterEvent | None:
    return (
        ResolveBitterEvent.objects.filter(player=player, event__is_resolved=False)
        .select_related("event", "battle")
        .first()
    )


def _get_active_looting_event(player) -> LootingEvent | None:
    return (
        LootingEvent.objects.filter(
            looting_player=player, event__is_resolved=False
        )
        .select_related("event", "looted_player")
        .first()
    )


# ---------------------------------------------------------------------------
# HoardTooFull view
# ---------------------------------------------------------------------------


class RatsHoardTooFullView(GameActionView):
    """HOARD_TOO_FULL event: player must discard one item from the overfull track.

    Scores 1 VP for the discarded item, then resolves the event.
    """

    action_name = "RATS_HOARD_TOO_FULL"
    faction = Faction.RATS
    faction_string = Faction.RATS.label

    def get(self, request, *args, **kwargs):
        game_id = int(request.query_params.get("game_id"))
        player = self.player(request, game_id)
        event = _get_active_hoard_event(player)
        options = self._item_options(player, event.track)
        track_label = HoardTooFullEvent.Track(event.track).label
        return self.generate_step(
            name="select_item",
            prompt=f"Your {track_label} track is over capacity. Discard one item (you score 1 VP).",
            endpoint="item",
            payload_details=[{"type": "item_id", "name": "item_id"}],
            options=options,
        )

    def _item_options(self, player, track: str):
        if track == HoardTooFullEvent.Track.COMMAND:
            entries = CommandItemEntry.objects.filter(player=player).select_related("item")
        else:
            entries = ProwessItemEntry.objects.filter(player=player).select_related("item")
        return [
            {"value": str(entry.item.id), "label": _item_label(entry.item)}
            for entry in entries
        ]

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "item":
                return self.post_item(request, game_id)
            case _:
                return Response(
                    {"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST
                )

    def post_item(self, request, game_id: int):
        player = self.player(request, game_id)
        item_id = request.data.get("item_id")
        try:
            item = Item.objects.get(id=int(item_id), game=player.game)
        except (Item.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"detail": "Item not found"})

        atomic_game_action(discard_hoard_item)(player, item)
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        if _get_active_hoard_event(player) is None:
            raise ValidationError({"detail": "No active HoardTooFull event"})


# ---------------------------------------------------------------------------
# ResolveBitter view
# ---------------------------------------------------------------------------


class RatsResolveBitterView(GameActionView):
    """BITTER_RESOLVE event: optionally absorb mobs to reinforce the Warlord's clearing.

    Player picks a clearing (Warlord's or adjacent) that contains a Mob token
    to absorb — removing the mob and placing a warrior in the Warlord's clearing.
    Repeat as desired, then press End to proceed to the dice roll.
    """

    action_name = "RATS_BITTER_RESOLVE"
    faction = Faction.RATS
    faction_string = Faction.RATS.label

    def get(self, request, *args, **kwargs):
        game_id = int(request.query_params.get("game_id"))
        player = self.player(request, game_id)
        options = self._mob_options(player)
        options.append({"value": "", "label": "End Bitter"})
        return self.generate_step(
            name="select_action",
            prompt="Bitter: absorb a nearby mob to place a warrior in the Warlord's clearing, or end.",
            endpoint="select",
            payload_details=[{"type": "clearing_number", "name": "clearing_number"}],
            options=options,
        )

    def _mob_options(self, player):
        warlord = get_warlord(player)
        if warlord.clearing is None:
            return []
        adjacent_and_local = list(warlord.clearing.connected_clearings.all()) + [warlord.clearing]
        options = []
        for clearing in adjacent_and_local:
            if Mob.objects.filter(player=player, clearing=clearing).exists():
                options.append({
                    "value": str(clearing.clearing_number),
                    "label": f"Absorb mob from clearing {clearing.clearing_number} ({clearing.suit})",
                })
        return options

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "select":
                return self.post_select(request, game_id)
            case _:
                return Response(
                    {"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST
                )

    def post_select(self, request, game_id: int):
        player = self.player(request, game_id)
        game = self.game(game_id)
        clearing_number = request.data.get("clearing_number", "")

        if clearing_number == "" or clearing_number is None:
            atomic_game_action(end_bitter)(player)
            return self.generate_completed_step()

        try:
            cn = int(clearing_number)
        except (ValueError, TypeError):
            raise ValidationError({"detail": "Invalid clearing number"})

        clearing = Clearing.objects.get(game=game, clearing_number=cn)
        atomic_game_action(absorb_mob)(player, clearing)

        # absorb_mob auto-calls end_bitter when no more mobs/warriors — check
        if _get_active_bitter_event(player) is None:
            return self.generate_completed_step()

        # Still more mobs to potentially absorb
        options = self._mob_options(player)
        options.append({"value": "", "label": "End Bitter"})
        return self.generate_step(
            name="select_action",
            prompt="Absorb another mob, or end.",
            endpoint="select",
            payload_details=[{"type": "clearing_number", "name": "clearing_number"}],
            options=options,
        )

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        if _get_active_bitter_event(player) is None:
            raise ValidationError({"detail": "No active Bitter resolve event"})


# ---------------------------------------------------------------------------
# Looting view
# ---------------------------------------------------------------------------


class RatsLootingView(GameActionView):
    """LOOTING event: player chooses which item to take from the looted player.

    Only created when the defender has multiple items (single-item loot is auto-resolved).
    """

    action_name = "RATS_LOOTING"
    faction = Faction.RATS
    faction_string = Faction.RATS.label

    def get(self, request, *args, **kwargs):
        game_id = int(request.query_params.get("game_id"))
        player = self.player(request, game_id)
        event = _get_active_looting_event(player)
        looted_player = event.looted_player
        options = self._item_options(looted_player)
        return self.generate_step(
            name="select_item",
            prompt=f"Looting: choose one item to take from {looted_player.faction}.",
            endpoint="item",
            payload_details=[{"type": "item_id", "name": "item_id"}],
            options=options,
        )

    def _item_options(self, looted_player):
        return [
            {"value": str(entry.item.id), "label": _item_label(entry.item)}
            for entry in CraftedItemEntry.objects.filter(
                player=looted_player
            ).select_related("item")
        ]

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "item":
                return self.post_item(request, game_id)
            case _:
                return Response(
                    {"error": "Invalid route"}, status=status.HTTP_400_BAD_REQUEST
                )

    def post_item(self, request, game_id: int):
        player = self.player(request, game_id)
        item_id = request.data.get("item_id")
        try:
            item = Item.objects.get(id=int(item_id), game=player.game)
        except (Item.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"detail": "Item not found"})

        atomic_game_action(choose_loot)(player, item)
        return self.generate_completed_step()

    def validate_timing(self, request, game_id: int, *args, **kwargs):
        player = self.player(request, game_id)
        if _get_active_looting_event(player) is None:
            raise ValidationError({"detail": "No active Looting event"})
