from rest_framework import serializers
from game.models.game_log import GameLog, LogType
from game.models.game_models import Game, Player, Card
from game.serializers.general_serializers import CardSerializer


# ==================
# SERIALIZERS
# ==================
class CatsBirdsForHireLogDetailsSerializer(serializers.Serializer):
    card = CardSerializer()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Discarded {obj['card']['title']} for an extra action"


class CatsMarchLogDetailsSerializer(serializers.Serializer):
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return "March"


class CatsWoodPlacementLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    count = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        count = obj.get("count", 1)
        suffix = "s" if count > 1 else ""
        return f"Placed {count} wood{suffix} at clearing {obj['clearing_number']}"


class CatsBuildLogDetailsSerializer(serializers.Serializer):
    building_type = serializers.CharField()
    clearing_number = serializers.IntegerField()
    wood_cost_count = serializers.IntegerField()
    points_scored = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        building_name = obj.get("building_type", "").replace("_", " ").lower()
        return f"Built {building_name} in clearing {obj['clearing_number']}"


class CatsOverworkLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    card = CardSerializer()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Overworked in clearing {obj['clearing_number']} (Played {obj['card']['title']})"


class CatsRecruitLogDetailsSerializer(serializers.Serializer):
    total_warriors = serializers.IntegerField()
    clearings_dict = serializers.DictField(child=serializers.IntegerField())
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Recruited {obj['total_warriors']} warriors"


class CatsFieldHospitalsLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    warriors_saved = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Field Hospitals! Saved {obj['warriors_saved']} warriors at clearing {obj['clearing_number']}"


class CatsSetupPickCornerLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Placed the Keep in clearing {obj['clearing_number']}"


class CatsSetupPlaceBuildingLogDetailsSerializer(serializers.Serializer):
    building_type = serializers.CharField()
    clearing_number = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        building_name = obj.get("building_type", "").replace("_", " ").lower()
        return f"Placed initial {building_name} in clearing {obj['clearing_number']}"


# ==================
# FACTORIES
# ==================
def log_cats_march(
    game: Game, player: Player, parent: GameLog | None = None
) -> GameLog:
    serializer = CatsMarchLogDetailsSerializer(data={})
    serializer.is_valid(raise_exception=True)

    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.CATS_MARCH,
        details=serializer.validated_data,
        parent=parent,
    )


def log_cats_wood_placement(
    game: Game,
    player: Player,
    clearing_number: int,
    count: int,
    parent: GameLog | None = None,
) -> GameLog:
    serializer = CatsWoodPlacementLogDetailsSerializer(
        data={"clearing_number": clearing_number, "count": count}
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.CATS_WOOD_PLACEMENT,
        details=serializer.validated_data,
        parent=parent,
    )


def log_cats_build(
    game: Game,
    player: Player,
    building_type: str,
    clearing_number: int,
    wood_cost_count: int,
    points_scored: int,
    parent: GameLog | None = None,
) -> GameLog:
    serializer = CatsBuildLogDetailsSerializer(
        data={
            "building_type": building_type,
            "clearing_number": clearing_number,
            "wood_cost_count": wood_cost_count,
            "points_scored": points_scored,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.CATS_BUILD,
        details=serializer.validated_data,
        parent=parent,
    )


def log_cats_birds_for_hire(
    game: Game, player: Player, card: Card, parent: GameLog | None = None
) -> GameLog:
    serializer = CatsBirdsForHireLogDetailsSerializer(
        data={
            "card": CardSerializer(card).data,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.CATS_BIRDS_FOR_HIRE,
        details=serializer.validated_data,
        parent=parent,
    )


def log_cats_overwork(
    game: Game,
    player: Player,
    clearing_number: int,
    card: Card,
    parent: GameLog | None = None,
) -> GameLog:
    serializer = CatsOverworkLogDetailsSerializer(
        data={
            "clearing_number": clearing_number,
            "card": CardSerializer(card).data,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.CATS_OVERWORK,
        details=serializer.validated_data,
        parent=parent,
    )


def log_cats_recruit(
    game: Game,
    player: Player,
    total_warriors: int,
    clearings_dict: dict[str, int],
    parent: GameLog | None = None,
) -> GameLog:
    serializer = CatsRecruitLogDetailsSerializer(
        data={
            "total_warriors": total_warriors,
            "clearings_dict": clearings_dict,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.CATS_RECRUIT,
        details=serializer.validated_data,
        parent=parent,
    )


def log_cats_field_hospitals(
    game: Game,
    player: Player,
    clearing_number: int,
    warriors_saved: int,
    parent: GameLog | None = None,
) -> GameLog:
    serializer = CatsFieldHospitalsLogDetailsSerializer(
        data={"clearing_number": clearing_number, "warriors_saved": warriors_saved}
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.CATS_FIELD_HOSPITALS,
        details=serializer.validated_data,
        parent=parent,
    )


def log_cats_setup_pick_corner(
    game: Game, player: Player, clearing_number: int, parent: GameLog | None = None
) -> GameLog:
    serializer = CatsSetupPickCornerLogDetailsSerializer(
        data={
            "clearing_number": clearing_number,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.CATS_SETUP_PICK_CORNER,
        details=serializer.validated_data,
        parent=parent,
    )


def log_cats_setup_place_building(
    game: Game,
    player: Player,
    building_type: str,
    clearing_number: int,
    parent: GameLog | None = None,
) -> GameLog:
    serializer = CatsSetupPlaceBuildingLogDetailsSerializer(
        data={
            "building_type": building_type,
            "clearing_number": clearing_number,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.CATS_SETUP_PLACE_BUILDING,
        details=serializer.validated_data,
        parent=parent,
    )


def get_current_march_log(game: Game, player: Player) -> GameLog | None:
    return (
        GameLog.objects.filter(game=game, player=player, log_type=LogType.CATS_MARCH)
        .order_by("-created_at")
        .first()
    )


def get_serializer_data(log: GameLog, details: dict, request=None):
    if log.log_type == LogType.CATS_WOOD_PLACEMENT:
        return CatsWoodPlacementLogDetailsSerializer(details).data
    if log.log_type == LogType.CATS_BUILD:
        return CatsBuildLogDetailsSerializer(details).data
    if log.log_type == LogType.CATS_OVERWORK:
        return CatsOverworkLogDetailsSerializer(details).data
    if log.log_type == LogType.CATS_BIRDS_FOR_HIRE:
        return CatsBirdsForHireLogDetailsSerializer(details).data
    if log.log_type == LogType.CATS_RECRUIT:
        return CatsRecruitLogDetailsSerializer(details).data
    if log.log_type == LogType.CATS_FIELD_HOSPITALS:
        return CatsFieldHospitalsLogDetailsSerializer(details).data
    if log.log_type == LogType.CATS_MARCH:
        return CatsMarchLogDetailsSerializer(details).data
    if log.log_type == LogType.CATS_SETUP_PICK_CORNER:
        return CatsSetupPickCornerLogDetailsSerializer(details).data
    if log.log_type == LogType.CATS_SETUP_PLACE_BUILDING:
        return CatsSetupPlaceBuildingLogDetailsSerializer(details).data
    return None
