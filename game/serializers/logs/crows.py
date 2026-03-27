from rest_framework import serializers
from game.models.game_log import GameLog, LogType
from game.models.game_models import Game, Player, Card, Clearing, Suit, Faction
from game.serializers.general_serializers import CardSerializer
from game.models.crows.tokens import PlotToken

# ==================
# SERIALIZERS
# ==================

class CrowsPlotLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    plot_type = serializers.CharField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        plot_label = obj.get("plot_type", "facedown").capitalize()
        if plot_label == "Facedown":
            return f"Placed a facedown plot in clearing {obj['clearing_number']}"
        return f"Placed a {plot_label} plot in clearing {obj['clearing_number']}"

    @classmethod
    def get_redacted_details(cls, details: dict) -> dict:
        redacted = dict(details)
        redacted["plot_type"] = "facedown"
        return redacted


class CrowsFlipLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    plot_type = serializers.CharField()
    points_scored = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        plot_label = obj.get("plot_type", "Unknown").capitalize()
        return f"Flipped a {plot_label} plot in clearing {obj['clearing_number']}, scoring {obj.get('points_scored', 0)} VP"


class CrowsRecruitLogDetailsSerializer(serializers.Serializer):
    suit = serializers.CharField()
    card = CardSerializer()
    clearing_count = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        suit_label = Suit(obj.get("suit", "b")).label
        return f"Recruited in {obj['clearing_count']} {suit_label} clearings"


class CrowsTrickLogDetailsSerializer(serializers.Serializer):
    clearing1 = serializers.IntegerField()
    clearing2 = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Tricked! Swapped plot tokens between clearing {obj['clearing1']} and {obj['clearing2']}"


class CrowsExposureLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    guessed_plot_type = serializers.CharField()
    card = CardSerializer()
    success = serializers.BooleanField()
    attacker_faction = serializers.CharField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        result = "Successfully exposed" if obj["success"] else "Failed to expose"
        guess = obj["guessed_plot_type"].capitalize()
        return f"{result} the plot in clearing {obj['clearing_number']} as a {guess}"


class CrowsRaidLogDetailsSerializer(serializers.Serializer):
    origin_clearing_number = serializers.IntegerField()
    warriors_placed = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Raid entry in clearing {obj['origin_clearing_number']}: Placed {obj.get('warriors_placed', 0)} warriors in adjacent clearings"


class CrowsSetupPlaceWarriorLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    suit = serializers.CharField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        suit_label = Suit(obj.get("suit", "b")).label
        return f"Placed initial Crow warrior in clearing {obj['clearing_number']} ({suit_label})"


class CrowsExtortionStoleCardLogDetailsSerializer(serializers.Serializer):
    victim_faction = serializers.CharField()
    card = CardSerializer(required=False, allow_null=True)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        victim = Faction(obj["victim_faction"]).label
        card = obj.get("card")
        if card:
            # Handle both model instance and serialized dict
            title = getattr(card, "title", None) or card.get("title", "a card")
            return f"Extortion! Stole {title} from {victim}"
        return f"Extortion! Stole a card from {victim}"

    @classmethod
    def get_redacted_details(cls, details: dict) -> dict:
        redacted = dict(details)
        redacted.pop("card", None)
        return redacted


# ==================
# FACTORIES
# ==================

def log_crows_plot(game: Game, player: Player, clearing_number: int, plot_type: str, parent: GameLog | None = None) -> GameLog:
    serializer = CrowsPlotLogDetailsSerializer(instance={
        "clearing_number": clearing_number,
        "plot_type": plot_type
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.CROWS_PLOT, details=serializer.data, parent=parent
    )

def log_crows_flip(game: Game, player: Player, clearing_number: int, plot_type: str, points_scored: int, parent: GameLog | None = None) -> GameLog:
    serializer = CrowsFlipLogDetailsSerializer(instance={
        "clearing_number": clearing_number,
        "plot_type": plot_type,
        "points_scored": points_scored
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.CROWS_FLIP, details=serializer.data, parent=parent
    )

def log_crows_recruit(game: Game, player: Player, suit: str, card: Card, clearing_count: int, parent: GameLog | None = None) -> GameLog:
    serializer = CrowsRecruitLogDetailsSerializer(instance={
        "suit": suit,
        "card": card,
        "clearing_count": clearing_count
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.CROWS_RECRUIT, details=serializer.data, parent=parent
    )

def log_crows_trick(game: Game, player: Player, clearing1: int, clearing2: int, parent: GameLog | None = None) -> GameLog:
    serializer = CrowsTrickLogDetailsSerializer(instance={
        "clearing1": clearing1,
        "clearing2": clearing2
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.CROWS_TRICK, details=serializer.data, parent=parent
    )

def log_crows_exposure(game: Game, explorer: Player, clearing_number: int, guessed_type: str, card: Card, success: bool, parent: GameLog | None = None) -> GameLog:
    serializer = CrowsExposureLogDetailsSerializer(instance={
        "clearing_number": clearing_number,
        "guessed_plot_type": guessed_type,
        "card": card,
        "success": success,
        "attacker_faction": explorer.faction
    })
    return GameLog.objects.create(
        game=game, player=explorer, log_type=LogType.CROWS_EXPOSURE, details=serializer.data, parent=parent
    )

def log_crows_raid(game: Game, player: Player, origin_number: int, warriors_placed: int, parent: GameLog | None = None) -> GameLog:
    serializer = CrowsRaidLogDetailsSerializer(instance={
        "origin_clearing_number": origin_number,
        "warriors_placed": warriors_placed
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.CROWS_RAID, details=serializer.data, parent=parent
    )

def log_crows_setup_place_warrior(game: Game, player: Player, clearing_number: int, suit: str, parent: GameLog | None = None) -> GameLog:
    serializer = CrowsSetupPlaceWarriorLogDetailsSerializer(instance={
        "clearing_number": clearing_number,
        "suit": suit
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.CROWS_SETUP_PLACE_WARRIOR, details=serializer.data, parent=parent
    )

def log_crows_extortion_stole_card(game: Game, player: Player, victim: Player, card: Card, parent: GameLog | None = None) -> GameLog:
    serializer = CrowsExtortionStoleCardLogDetailsSerializer(instance={
        "victim_faction": victim.faction,
        "card": card
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.CROWS_EXTORTION_STOLE_CARD, details=serializer.data, parent=parent
    )


def get_serializer_data(log: GameLog, details: dict, request=None):
    if log.log_type == LogType.CROWS_PLOT:
        data = dict(details)
        if request and hasattr(request, "user"):
            if log.player and log.player.user != request.user:
                data = CrowsPlotLogDetailsSerializer.get_redacted_details(data)
        return CrowsPlotLogDetailsSerializer(data).data
    if log.log_type == LogType.CROWS_FLIP:
        return CrowsFlipLogDetailsSerializer(details).data
    if log.log_type == LogType.CROWS_RECRUIT:
        return CrowsRecruitLogDetailsSerializer(details).data
    if log.log_type == LogType.CROWS_TRICK:
        return CrowsTrickLogDetailsSerializer(details).data
    if log.log_type == LogType.CROWS_EXPOSURE:
        return CrowsExposureLogDetailsSerializer(details).data
    if log.log_type == LogType.CROWS_RAID:
        return CrowsRaidLogDetailsSerializer(details).data
    if log.log_type == LogType.CROWS_SETUP_PLACE_WARRIOR:
        return CrowsSetupPlaceWarriorLogDetailsSerializer(details).data
    if log.log_type == LogType.CROWS_EXTORTION_STOLE_CARD:
        data = dict(details)
        if request and hasattr(request, "user"):
            if log.player and log.player.user != request.user:
                data = CrowsExtortionStoleCardLogDetailsSerializer.get_redacted_details(data)
        return CrowsExtortionStoleCardLogDetailsSerializer(data).data
    return None
