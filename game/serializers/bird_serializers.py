from game.models.birds.player import Vizier
from rest_framework import serializers

from game.models.birds.buildings import BirdRoost
from game.models.birds.player import BirdLeader, DecreeEntry
from game.models.game_models import Building, Player, Warrior
from game.serializers.general_serializers import (
    BuildingSerializer,
    CardSerializer,
    PlayerPublicSerializer,
    WarriorSerializer,
)


class RoostSerializer(serializers.ModelSerializer):
    building = BuildingSerializer()
    crafted_with = serializers.BooleanField()

    class Meta:
        model = BirdRoost
        fields = ["building", "crafted_with"]


class BirdBuildingSerializer(serializers.Serializer):
    """Serializer for bird buildings. collects lists of all buildings"""

    roosts = RoostSerializer(many=True)


class BirdDecreeEntrySerializer(serializers.ModelSerializer):
    card = CardSerializer()

    class Meta:
        model = DecreeEntry
        fields = ["column", "fulfilled", "card"]

class VizierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vizier
        fields = ["column", "fulfilled"]

class BirdLeaderSerializer(serializers.ModelSerializer):
    leader_display = serializers.CharField(source="get_leader_display")

    class Meta:
        model = BirdLeader
        fields = ["leader", "leader_display", "available", "active"]


class BirdSerializer(serializers.Serializer):
    """Serializer to provide all (public) information about birds"""

    player = PlayerPublicSerializer()
    buildings = BirdBuildingSerializer()
    warriors = WarriorSerializer(many=True)
    leaders = BirdLeaderSerializer(many=True)
    decree = BirdDecreeEntrySerializer(many=True)
    viziers = VizierSerializer(many=True)

    @classmethod
    def from_player(cls, player: Player):
        roosts = BirdRoost.objects.filter(player=player)
        buildings = {"roosts": roosts}
        warriors = Warrior.objects.filter(player=player)
        leaders = BirdLeader.objects.filter(player=player)
        decree = DecreeEntry.objects.filter(player=player)
        viziers = Vizier.objects.filter(player=player)
        print(f"viziers: {viziers}")
        return cls(
            instance={
                "player": player,
                "buildings": buildings,
                "warriors": warriors,
                "leaders": leaders,
                "decree": decree,
                "viziers": viziers,
            }
        )
