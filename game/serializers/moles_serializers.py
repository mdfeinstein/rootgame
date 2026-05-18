from rest_framework import serializers

from game.models.game_models import Player, Warrior
from game.models.moles.buildings import Citadel, Market
from game.models.moles.tokens import Tunnel
from game.models.moles.turn import MoleTurn, MoleBirdsong, MoleDaylight, MoleEvening
from game.models.moles.ministers import Minister
from game.models.moles.crown import Crown
from game.serializers.general_serializers import (
    BuildingSerializer,
    PlayerPublicSerializer,
    TokenSerializer,
    WarriorSerializer,
)


class MolesMinisterSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Minister
        fields = ["name", "swayed", "used", "crown_type"]

    def get_name(self, obj):
        return obj.get_name_display()


class MolesCrownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crown
        fields = ["type", "used"]


class MolesCitadelSerializer(serializers.ModelSerializer):
    building = BuildingSerializer()

    class Meta:
        model = Citadel
        fields = ["building", "crafted_with"]


class MolesMarketSerializer(serializers.ModelSerializer):
    building = BuildingSerializer()

    class Meta:
        model = Market
        fields = ["building", "crafted_with"]


class MolesBuildingsSerializer(serializers.Serializer):
    """Serializer for moles buildings. collects lists of all buildings"""

    citadels = MolesCitadelSerializer(many=True)
    markets = MolesMarketSerializer(many=True)


class MolesTokensSerializer(serializers.Serializer):
    """Serializer for moles tokens. collects lists of all tokens"""

    class NestedTokenSerializer(serializers.Serializer):
        token = TokenSerializer()

    tunnels = NestedTokenSerializer(many=True)


class MolesBirdsongSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoleBirdsong
        fields = ["step"]


class MolesDaylightSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoleDaylight
        fields = ["step", "actions_left", "brigadier_action"]


class MolesEveningSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoleEvening
        fields = ["step"]


class MoleTurnSerializer(serializers.ModelSerializer):
    birdsong = MolesBirdsongSerializer(read_only=True)
    daylight = MolesDaylightSerializer(read_only=True)
    evening = MolesEveningSerializer(read_only=True)

    class Meta:
        model = MoleTurn
        fields = ["turn_number", "birdsong", "daylight", "evening"]


class MolesSerializer(serializers.Serializer):
    """Serializer to provide all (public) information about moles"""

    player = PlayerPublicSerializer()
    warriors = WarriorSerializer(many=True)
    buildings = MolesBuildingsSerializer()
    tokens = MolesTokensSerializer()
    ministers = MolesMinisterSerializer(many=True)
    crowns = MolesCrownSerializer(many=True)
    burrow_warriors = serializers.SerializerMethodField()

    @classmethod
    def from_player(cls, player: Player):
        warriors = Warrior.objects.filter(player=player)
        citadels = Citadel.objects.filter(player=player)
        markets = Market.objects.filter(player=player)
        tunnels = Tunnel.objects.filter(player=player)

        buildings = {
            "citadels": citadels,
            "markets": markets,
        }

        tokens = {
            "tunnels": tunnels,
        }

        ministers = Minister.objects.filter(player=player)
        crowns = Crown.objects.filter(player=player)

        # Count warriors in burrow (warriors with no clearing)
        burrow_count = Warrior.objects.filter(
            player=player, clearing__isnull=False, clearing__clearing_number=0
        ).count()

        return cls(
            instance={
                "player": player,
                "warriors": warriors,
                "buildings": buildings,
                "tokens": tokens,
                "ministers": ministers,
                "crowns": crowns,
                "burrow_warriors": burrow_count,
            }
        )

    def get_burrow_warriors(self, obj):
        return obj.get("burrow_warriors", 0)
