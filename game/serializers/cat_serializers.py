from rest_framework import serializers

from game.models.cats.buildings import CatBuildingTypes, Recruiter, Sawmill, Workshop
from game.models.cats.tokens import CatKeep, CatWood
from game.models.game_models import Player, Warrior
from game.serializers.general_serializers import (
    BuildingSerializer,
    PlayerPublicSerializer,
    TextChoiceLabelField,
    TokenSerializer,
    WarriorSerializer,
)


class WorkShopSerializer(serializers.ModelSerializer):
    building = BuildingSerializer()

    class Meta:
        model = Workshop
        fields = ["building", "crafted_with"]


class RecruiterSerializer(serializers.ModelSerializer):
    building = BuildingSerializer()

    class Meta:
        model = Recruiter
        fields = ["building", "used"]


class SawmillSerializer(serializers.ModelSerializer):
    building = BuildingSerializer()

    class Meta:
        model = Sawmill
        fields = ["building", "used"]


class CatBuildingSerializer(serializers.Serializer):
    """Serializer for cat buildings. collects lists of all buildings"""

    workshops = WorkShopSerializer(many=True)
    recruiters = RecruiterSerializer(many=True)
    sawmills = SawmillSerializer(many=True)


class CatTokenSerializer(serializers.Serializer):
    """Serializer for cat tokens. collects lists of all tokens"""

    class NestedTokenSerializer(serializers.Serializer):
        # want to nest the
        token = TokenSerializer()

    # while keep usually cant be many, useful to keep the token structure uniform
    keep = NestedTokenSerializer(many=True)
    wood = NestedTokenSerializer(many=True)


class CatSerializer(serializers.Serializer):
    """Serializer to provide all (public) information about cats"""

    player = PlayerPublicSerializer()
    tokens = CatTokenSerializer()
    buildings = CatBuildingSerializer()
    warriors = WarriorSerializer(many=True)

    @classmethod
    def from_player(cls, player: Player):
        keep = CatKeep.objects.filter(player=player)
        wood = CatWood.objects.filter(player=player)

        tokens = {"keep": keep, "wood": wood}

        warriors = Warrior.objects.filter(player=player)

        workshops = Workshop.objects.filter(player=player)
        recruiters = Recruiter.objects.filter(player=player)
        sawmills = Sawmill.objects.filter(player=player)
        buildings = {
            "workshops": workshops,
            "recruiters": recruiters,
            "sawmills": sawmills,
        }

        return cls(
            instance={
                "player": player,
                "tokens": tokens,
                "buildings": buildings,
                "warriors": warriors,
            }
        )
