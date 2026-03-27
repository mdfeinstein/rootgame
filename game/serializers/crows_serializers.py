from rest_framework import serializers

from game.models.game_models import Player, Warrior
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowTurn, CrowBirdsong, CrowDaylight, CrowEvening
from game.serializers.general_serializers import (
    PlayerPublicSerializer,
    WarriorSerializer,
    CardSerializer,
)


class CrowPlotTokenSerializer(serializers.ModelSerializer):
    clearing_number = serializers.SerializerMethodField()

    class Meta:
        model = PlotToken
        fields = ["id", "plot_type", "is_facedown", "clearing_number", "crafted_with"]

    def get_clearing_number(self, obj):
        return obj.clearing.clearing_number if obj.clearing else None

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        is_private = self.context.get("is_private", False)
        if instance.is_facedown and not is_private:
            ret["plot_type"] = None

        return ret


class CrowBirdsongSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrowBirdsong
        fields = ["step"]


class CrowDaylightSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrowDaylight
        fields = ["step", "actions_remaining", "plots_placed"]


class CrowEveningSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrowEvening
        fields = ["step", "cards_drawn", "exert_used"]


class CrowTurnSerializer(serializers.ModelSerializer):
    birdsong = CrowBirdsongSerializer(read_only=True)
    daylight = CrowDaylightSerializer(read_only=True)
    evening = CrowEveningSerializer(read_only=True)

    class Meta:
        model = CrowTurn
        fields = ["turn_number", "birdsong", "daylight", "evening"]


from game.models.crows.exposure import ExposureGuessedPlot, ExposureRevealedCards


class ExposureGuessedPlotSerializer(serializers.ModelSerializer):
    clearing_number = serializers.IntegerField(source="clearing.clearing_number")
    faction = serializers.CharField(source="player.faction")

    class Meta:
        model = ExposureGuessedPlot
        fields = ["clearing_number", "guessed_plot_type", "faction", "turn_number"]


class CrowsTokenSerializer(serializers.Serializer):
    def to_representation(self, instance):
        # instance is a dict of {type_name: [plots]}
        ret = {}
        for type_name, plots in instance.items():
            ret[type_name] = [
                {"token": CrowPlotTokenSerializer(p, context=self.context).data}
                for p in plots
            ]
        return ret


class CrowsSerializer(serializers.Serializer):
    """Serializer to provide all (public) information about crows"""

    player = PlayerPublicSerializer()
    tokens = CrowsTokenSerializer()
    warriors = WarriorSerializer(many=True)
    reserve_plots_count = serializers.IntegerField(read_only=True)
    exposure_guessed_plots = ExposureGuessedPlotSerializer(many=True)

    @classmethod
    def from_player(cls, player: Player):
        tokens_plots = PlotToken.objects.filter(player=player, clearing__isnull=False)

        token_groups = {}
        for p in tokens_plots:
            label = "?" if p.is_facedown else p.plot_type.capitalize()
            if label not in token_groups:
                token_groups[label] = []
            token_groups[label].append(p)

        warriors = Warrior.objects.filter(player=player)
        reserve_plots_count = PlotToken.objects.filter(
            player=player, clearing__isnull=True
        ).count()
        guessed_plots = ExposureGuessedPlot.objects.filter(player__game=player.game)

        return cls(
            instance={
                "player": player,
                "tokens": token_groups,
                "warriors": warriors,
                "reserve_plots_count": reserve_plots_count,
                "exposure_guessed_plots": guessed_plots,
            },
            context={"is_private": False},
        )


class CrowsPrivateSerializer(serializers.Serializer):
    reserve_plots = serializers.SerializerMethodField()
    facedown_plots = serializers.SerializerMethodField()
    exposure_revealed_cards = CardSerializer(many=True)

    def get_reserve_plots(self, obj):
        serializer = CrowPlotTokenSerializer(
            obj["reserve_plots"], many=True, context={"is_private": True}
        )
        return serializer.data

    def get_facedown_plots(self, obj):
        serializer = CrowPlotTokenSerializer(
            obj["facedown_plots"], many=True, context={"is_private": True}
        )
        return serializer.data
