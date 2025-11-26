from rest_framework import serializers

from game.models.game_models import Player, Warrior
from game.models.wa.buildings import WABase
from game.models.wa.player import OfficerEntry, SupporterStackEntry
from game.models.wa.tokens import WASympathy
from game.serializers.general_serializers import (
    BuildingSerializer,
    PlayerPublicSerializer,
    TokenSerializer,
    WarriorSerializer,
)


class WABaseSerializer(serializers.ModelSerializer):
    building = BuildingSerializer(read_only=True)
    suit = serializers.CharField(read_only=True)

    class Meta:
        model = WABase
        fields = ["building", "suit"]


class WASympathySerializer(serializers.ModelSerializer):
    token = TokenSerializer()
    crafted_with = serializers.BooleanField(read_only=True)

    class Meta:
        model = WASympathy
        fields = ["token", "crafted_with"]


class WATokenSerializer(serializers.Serializer):
    sympathy = WASympathySerializer(many=True)


class WABuildingSerializer(serializers.Serializer):
    base = WABaseSerializer(many=True)


class WASerializer(serializers.Serializer):
    """Serializer to provide all (public) information about wa"""

    player = PlayerPublicSerializer()
    tokens = WATokenSerializer()
    buildings = WABuildingSerializer()
    warriors = WarriorSerializer(many=True)
    supporter_count = serializers.IntegerField(read_only=True)
    officer_count = serializers.IntegerField(read_only=True)

    @classmethod
    def from_player(cls, player: Player):
        tokens_sympathy = WASympathy.objects.filter(player=player)
        tokens = {"sympathy": tokens_sympathy}

        bases = WABase.objects.filter(player=player)
        buildings = {"base": bases}

        warriors = Warrior.objects.filter(player=player)

        supporter_count = SupporterStackEntry.objects.filter(player=player).count()
        officer_count = OfficerEntry.objects.filter(player=player).count()

        return cls(
            instance={
                "player": player,
                "tokens": tokens,
                "buildings": buildings,
                "warriors": warriors,
                "supporter_count": supporter_count,
                "officer_count": officer_count,
            }
        )
