from rest_framework import serializers

from game.models.game_models import Player
from game.models.rats.buildings import Stronghold
from game.models.rats.tokens import Mob, Warlord
from game.models.rats.player import CurrentMood, CommandItemEntry, ProwessItemEntry
from game.models.rats.turn import RatsTurn, RatsBirdsong, RatsDaylight, RatsEvening
from game.models.rats.setup import RatsSimpleSetup
from game.queries.rats.pieces import get_warlord, get_warriors
from game.queries.rats.birdsong import get_valid_moods
from game.serializers.general_serializers import (
    BuildingSerializer,
    PlayerPublicSerializer,
    TokenSerializer,
    WarriorSerializer,
)


class StrongholdSerializer(serializers.ModelSerializer):
    building = BuildingSerializer()

    class Meta:
        model = Stronghold
        fields = ["building", "crafted_with"]


class MobSerializer(serializers.ModelSerializer):
    token = TokenSerializer()

    class Meta:
        model = Mob
        fields = ["token"]


class WarlordSerializer(serializers.ModelSerializer):
    clearing_number = serializers.SerializerMethodField()

    class Meta:
        model = Warlord
        fields = ["clearing_number"]

    def get_clearing_number(self, obj: Warlord) -> int | None:
        return obj.clearing.clearing_number if obj.clearing is not None else None


class CurrentMoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrentMood
        fields = ["mood_type"]



class CommandItemEntrySerializer(serializers.ModelSerializer):
    item_id = serializers.IntegerField(source="item.id")
    item_type = serializers.CharField(source="item.item_type")

    class Meta:
        model = CommandItemEntry
        fields = ["item_id", "item_type"]


class ProwessItemEntrySerializer(serializers.ModelSerializer):
    item_id = serializers.IntegerField(source="item.id")
    item_type = serializers.CharField(source="item.item_type")

    class Meta:
        model = ProwessItemEntry
        fields = ["item_id", "item_type"]


class RatsBirdsongSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatsBirdsong
        fields = ["step"]


class RatsDaylightSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatsDaylight
        fields = ["step", "commands_used", "prowess_used"]


class RatsEveningSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatsEvening
        fields = ["step"]


class RatsTurnSerializer(serializers.ModelSerializer):
    birdsong = RatsBirdsongSerializer(read_only=True)
    daylight = RatsDaylightSerializer(read_only=True)
    evening = RatsEveningSerializer(read_only=True)

    class Meta:
        model = RatsTurn
        fields = ["turn_number", "birdsong", "daylight", "evening"]


class RatsSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatsSimpleSetup
        fields = ["step"]


class RatsBuildingsSerializer(serializers.Serializer):
    """Wraps Rats buildings under a 'buildings' key so the frontend buildingTable hook can tabulate them."""
    strongholds = StrongholdSerializer(many=True)


class RatsSerializer(serializers.Serializer):
    """Serializer to provide all (public) information about rats (Lord of the Hundreds)."""

    player = PlayerPublicSerializer()
    warriors = WarriorSerializer(many=True)
    warlord = WarlordSerializer()
    buildings = RatsBuildingsSerializer()
    mobs = MobSerializer(many=True)
    mood = CurrentMoodSerializer()
    valid_moods = serializers.ListField(
        child=serializers.ChoiceField(choices=CurrentMood.MoodType.choices)
    )
    command_items = CommandItemEntrySerializer(many=True)
    prowess_items = ProwessItemEntrySerializer(many=True)

    @classmethod
    def from_player(cls, player: Player):
        strongholds = Stronghold.objects.filter(player=player)
        return cls(
            instance={
                "player": player,
                "warriors": get_warriors(player),
                "warlord": get_warlord(player),
                "buildings": {"strongholds": strongholds},
                "mobs": Mob.objects.filter(player=player),
                "mood": CurrentMood.objects.get(player=player),
                "valid_moods": [m.value for m in get_valid_moods(player)],
                "command_items": CommandItemEntry.objects.filter(player=player),
                "prowess_items": ProwessItemEntry.objects.filter(player=player),
            }
        )
