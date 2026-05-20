from rest_framework import serializers

from game.models.game_log import GameLog, LogType
from game.models.game_models import Game, Player
from game.serializers.logs.general import CardSerializer


class RatsBuildLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    card = serializers.DictField()

    def get_text(self, obj):
        return f"Built a Stronghold in clearing {obj['clearing_number']} (spent {obj['card']['title']})"


def log_rats_build(
    game: Game,
    player: Player,
    clearing_number: int,
    card,
    parent: GameLog | None = None,
) -> GameLog:
    serializer = RatsBuildLogDetailsSerializer(
        data={
            "clearing_number": clearing_number,
            "card": CardSerializer(card).data,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.RATS_BUILD,
        details=serializer.validated_data,
        parent=parent,
    )


def get_serializer_data(log: GameLog, details: dict, request=None):
    if log.log_type == LogType.RATS_BUILD:
        s = RatsBuildLogDetailsSerializer(details)
        data = dict(s.data)
        data["text"] = s.get_text(details)
        return data
    return None
