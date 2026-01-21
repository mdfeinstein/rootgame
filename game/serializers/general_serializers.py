from rest_framework import serializers
from django.contrib.auth.models import User
from game.models.birds.setup import BirdsSimpleSetup
from game.models.birds.turn import BirdTurn
from game.models.cats.setup import CatsSimpleSetup
from game.models.cats.turn import CatTurn
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import (
    Building,
    BuildingSlot,
    Card,
    Clearing,
    Faction,
    Game,
    HandEntry,
    Player,
    Warrior,
    Token,
)
from game.models.wa.turn import WATurn
from game.models.game_models import CraftedCardEntry
from game.queries.cards.active_effects import can_use_card, has_active_effect, is_used





class CardSerializer(serializers.ModelSerializer):
    card_name = serializers.SerializerMethodField()
    suit_name = serializers.CharField(source="get_suit_display", required=False)
    title = serializers.CharField()
    text = serializers.CharField()
    craftable = serializers.BooleanField()
    cost = serializers.ListField()
    item = serializers.CharField()
    item_name = serializers.CharField()
    crafted_points = serializers.IntegerField()
    ambush = serializers.BooleanField()
    dominance = serializers.BooleanField()

    class Meta:
        model = Card
        fields = [
            "id",
            "card_name",
            "suit",
            "suit_name",
            "title",
            "text",
            "craftable",
            "cost",
            "item",
            "item_name",
            "crafted_points",
            "ambush",
            "dominance",
        ]

    def get_card_name(self, card: Card):
        return card.enum.name



class CraftedCardSerializer(serializers.ModelSerializer):
    card = CardSerializer()
    has_active = serializers.SerializerMethodField()
    used = serializers.SerializerMethodField()
    action_endpoint = serializers.SerializerMethodField()

    class Meta:
        model = CraftedCardEntry
        fields = [
            "card",
            "has_active",
            "used",
            "action_endpoint",
        ]

    def get_has_active(self, crafted_card: CraftedCardEntry) -> bool:
        return has_active_effect(crafted_card)

    def get_used(self, crafted_card: CraftedCardEntry) -> bool:
        return is_used(crafted_card)

    def get_action_endpoint(self, crafted_card: CraftedCardEntry) -> str | None:
        if can_use_card(crafted_card.player, crafted_card):
            slug = crafted_card.card.enum.name.lower().replace("_", "-")
            return f"api/action/card/{slug}/"
        return None


class WarriorSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source="player.user.username")
    clearing_number = serializers.SerializerMethodField()

    class Meta:
        model = Warrior
        fields = [
            "player_name",
            "clearing_number",
        ]

    def get_clearing_number(self, warrior: Warrior) -> int | None:
        return (
            warrior.clearing.clearing_number if warrior.clearing is not None else None
        )


class BuildingSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source="player.user.username")
    clearing_number = clearing_number = serializers.SerializerMethodField()
    building_slot_number = serializers.SerializerMethodField()

    class Meta:
        model = Building
        fields = [
            "player_name",
            "clearing_number",
            "building_slot_number",
        ]

    def get_clearing_number(self, building: Building) -> int | None:
        building_slot = building.building_slot
        return (
            building_slot.clearing.clearing_number
            if building_slot is not None
            else None
        )

    def get_building_slot_number(self, building: Building) -> int | None:
        building_slot = building.building_slot
        return building_slot.building_slot_number if building_slot is not None else None


class TokenSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source="player.user.username")
    clearing_number = serializers.SerializerMethodField()

    class Meta:
        model = Token
        fields = [
            "player_name",
            "clearing_number",
        ]

    def get_clearing_number(self, token: Token) -> int | None:
        clearing = getattr(token, "clearing", None)
        return clearing.clearing_number if clearing is not None else None


class ClearingSerializer(serializers.ModelSerializer):
    suit_name = serializers.CharField(source="get_suit_display")
    connected_to = serializers.SerializerMethodField()
    water_connected_to = serializers.SerializerMethodField()

    class Meta:
        model = Clearing
        fields = [
            "suit_name",
            "suit",
            "clearing_number",
            "connected_to",
            "water_connected_to",
        ]

    def get_connected_to(self, clearing: Clearing) -> list[int]:
        return [
            clearing.clearing_number for clearing in clearing.connected_clearings.all()
        ]

    def get_water_connected_to(self, clearing: Clearing) -> list[int]:
        return [
            clearing.clearing_number
            for clearing in clearing.water_connected_clearings.all()
        ]


class PlayerPublicSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username")
    faction = serializers.CharField()  # this will be two char stub...
    faction_label = serializers.CharField()
    score = serializers.IntegerField()
    turn_order = serializers.IntegerField()
    card_count = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = [
            "username",
            "faction",
            "faction_label",
            "score",
            "turn_order",
            "card_count",
        ]

    def get_card_count(self, player: Player) -> int:
        return HandEntry.objects.filter(player=player).count()


class PlayerPrivateSerializer(serializers.ModelSerializer):
    cards_in_hand = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = ["cards_in_hand"]

    def get_cards_in_hand(self, player: Player):
        hand_cards = HandEntry.objects.filter(player=player).select_related("card")
        cards = [hand_card.card for hand_card in hand_cards]
        return CardSerializer(cards, many=True).data


class TextChoiceLabelField(serializers.ChoiceField):
    def to_internal_value(self, data):
        # Accept label or value
        for value, label in self.choices.items():
            if data == label or data == value:
                return value
        self.fail("invalid_choice", input=data)


class FactionChoiceSerializer(serializers.Serializer):
    faction = TextChoiceLabelField(choices=Faction.choices)


class CreateNewGameSerializer(serializers.Serializer):
    map_label = TextChoiceLabelField(
        choices=Game.BoardMaps.choices, required=False, allow_null=True
    )
    faction_options = FactionChoiceSerializer(
        many=True, required=False, allow_null=True
    )


class PayloadEntry(serializers.Serializer):
    type = serializers.CharField()
    name = serializers.CharField()
    value = serializers.SerializerMethodField(allow_null=True, required=False)

    def get_value(self, payload_entry):
        # handle more types as we add them in.
        if payload_entry["type"] == "clearing_number":
            try:
                return int(payload_entry["value"])
            except KeyError:
                return None
        try:
            return payload_entry["value"]
        except KeyError:
            return None


class OptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField(required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get("label"):
            data["label"] = data["value"]
        return data


class GameActionStepSerializer(serializers.Serializer):
    faction = serializers.CharField(required=False)
    name = serializers.CharField()
    prompt = serializers.CharField(required=False)
    endpoint = serializers.CharField(required=False)
    payload_details = serializers.ListField(
        child=PayloadEntry(), allow_empty=True, required=False
    )
    accumulated_payload = serializers.JSONField(required=False)
    options = OptionSerializer(many=True, required=False)


class GameActionSerializer(serializers.Serializer):
    name = serializers.CharField()
    route = serializers.CharField()


class GameStatusSerializer(serializers.Serializer):
    """
    Serializer for information on the current game status
    This includes the current turn information as well as any relevant events
    """

    game_status = serializers.ChoiceField(choices=Game.GameStatus.choices)
    setup_status = serializers.ChoiceField(
        choices=GameSimpleSetup.GameSetupStatus.choices, required=False
    )
    current_turn_player = serializers.CharField(required=False)
    # current_setup_object = serializers.SerializerMethodField(required=False)
    # current_event_object = GameEventSerializer(required=False)

    # TODO: event queue serializer (or just one event at a time?)

    @classmethod
    def from_game(cls, game: Game):
        setup_status = GameSimpleSetup.objects.get(game=game).status
        current_player = Player.objects.get(game=game, turn_order=game.current_turn)
        # if in setup, use setup turn objects
        if game.status == Game.GameStatus.STARTED:
            turn_object_dict = {
                Faction.CATS: CatsSimpleSetup,
                Faction.BIRDS: BirdsSimpleSetup,
                Faction.WOODLAND_ALLIANCE: None,  #
            }
        elif game.status == Game.GameStatus.SETUP_COMPLETED:
            turn_object_dict = {
                Faction.CATS: CatTurn,
                Faction.BIRDS: BirdTurn,
                Faction.WOODLAND_ALLIANCE: WATurn,
            }
        if current_player is not None:
            print(game.status)
            print(current_player.faction)
            print(turn_object_dict)
            faction = Faction(current_player.faction)
            print(faction)
            turn_object = (
                turn_object_dict[faction]
                .objects.filter(player=current_player)
                .order_by("-turn_number")
                .first()
            )
            player_name = current_player.user.username
        else:
            turn_object = None
            player_name = None

        return cls(
            instance={
                "game_status": game.status,
                "setup_status": setup_status,
                "current_turn_player": player_name,
                "current_turn_object": turn_object,
            }
        )


class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField()

    class Meta:
        model = User
        fields = ["username"]


class PlayerSerializer(serializers.Serializer):
    faction = serializers.CharField()
    faction_label = serializers.SerializerMethodField()

    def get_faction_label(self, player: Player):
        return Faction(player.faction).label
