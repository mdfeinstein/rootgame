from rest_framework import serializers

from game.models.game_models import Player, Warrior
from game.models.moles.buildings import Citadel, Market
from game.models.moles.tokens import Tunnel
from game.models.moles.turn import MoleTurn, MoleBirdsong, MoleDaylight, MoleEvening
from game.models.moles.ministers import Minister
from game.models.moles.crown import Crown
from game.serializers.general_serializers import (
    PlayerPublicSerializer,
    WarriorSerializer,
)


class MolesMinisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Minister
        fields = ["id", "name", "swayed", "used", "crown_type"]


class MolesCrownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crown
        fields = ["id", "tier", "used", "minister"]


class MolesCitadelSerializer(serializers.ModelSerializer):
    clearing_number = serializers.SerializerMethodField()

    class Meta:
        model = Citadel
        fields = ["id", "clearing_number", "crafted_with"]

    def get_clearing_number(self, obj):
        return obj.clearing.clearing_number if obj.clearing else None


class MolesMarketSerializer(serializers.ModelSerializer):
    clearing_number = serializers.SerializerMethodField()

    class Meta:
        model = Market
        fields = ["id", "clearing_number", "crafted_with"]

    def get_clearing_number(self, obj):
        return obj.clearing.clearing_number if obj.clearing else None


class MolesTunnelSerializer(serializers.ModelSerializer):
    clearing_number = serializers.SerializerMethodField()

    class Meta:
        model = Tunnel
        fields = ["id", "clearing_number"]

    def get_clearing_number(self, obj):
        return obj.clearing.clearing_number if obj.clearing else None


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
    citadels = MolesCitadelSerializer(many=True)
    markets = MolesMarketSerializer(many=True)
    tunnels = MolesTunnelSerializer(many=True)
    ministers = MolesMinisterSerializer(many=True)
    crowns = MolesCrownSerializer(many=True)
    burrow_warriors = serializers.SerializerMethodField()

    @classmethod
    def from_player(cls, player: Player):
        warriors = Warrior.objects.filter(player=player)
        citadels = Citadel.objects.filter(player=player)
        markets = Market.objects.filter(player=player)
        tunnels = Tunnel.objects.filter(player=player)
        ministers = Minister.objects.filter(player=player)
        crowns = Crown.objects.filter(minister__player=player)

        # Count warriors in burrow (warriors with no clearing)
        burrow_count = Warrior.objects.filter(player=player, clearing__isnull=True).count()

        return cls(
            instance={
                "player": player,
                "warriors": warriors,
                "citadels": citadels,
                "markets": markets,
                "tunnels": tunnels,
                "ministers": ministers,
                "crowns": crowns,
                "burrow_warriors": burrow_count,
            }
        )

    def get_burrow_warriors(self, obj):
        return obj.get("burrow_warriors", 0)
