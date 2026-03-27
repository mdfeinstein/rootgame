from game.models import Faction, Suit
from rest_framework import serializers
from game.models.game_log import GameLog, LogType
from game.models.game_models import Game, Player, Card
from game.serializers.general_serializers import CardSerializer


# ==================
# SERIALIZERS
# ==================


class TurnLogDetailsSerializer(serializers.Serializer):
    turn_number = serializers.IntegerField(required=False)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        turn_number = obj.get("turn_number", "?")
        return f"Turn {turn_number}"


class PhaseLogDetailsSerializer(serializers.Serializer):
    phase = serializers.CharField(required=False)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        phase = obj.get("phase", "Unknown")
        return f"{phase} Phase"


class MoveLogDetailsSerializer(serializers.Serializer):
    origin_clearing_number = serializers.IntegerField()
    dest_clearing_number = serializers.IntegerField()
    warriors_moved = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Moved {obj['warriors_moved']} warriors to clearing {obj['dest_clearing_number']}"


class CraftLogDetailsSerializer(serializers.Serializer):
    card = CardSerializer()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Crafted card {obj['card']['title']}"


class BattleLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    attacker_faction = serializers.CharField()
    defender_faction = serializers.CharField()
    battle_id = serializers.IntegerField(required=False)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        defender = Faction(obj["defender_faction"]).label
        return (
            f"Initiated Battle against {defender} in clearing {obj['clearing_number']}"
        )


class DrawLogDetailsSerializer(serializers.Serializer):
    cards = CardSerializer(many=True, required=False)
    count = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        if "cards" in obj:
            card_names = ", ".join(c["title"] for c in obj["cards"])
            return f"Drew {obj['count']} cards: {card_names}"
        return f"Drew {obj['count']} cards"

    @classmethod
    def get_redacted_details(cls, details: dict) -> dict:
        redacted = dict(details)
        redacted.pop("cards", None)
        return redacted


class DiscardLogDetailsSerializer(serializers.Serializer):
    card = CardSerializer()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Discarded {obj['card']['title']}"


class AmbushLogDetailsSerializer(serializers.Serializer):
    card = CardSerializer()
    faction = serializers.CharField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        faction = Faction(obj["faction"]).label
        suit_label = obj["card"]["suit"]["label"]
        return f"{faction} played Ambush ({suit_label})"


class DiceRollLogDetailsSerializer(serializers.Serializer):
    attacker_roll = serializers.IntegerField()
    defender_roll = serializers.IntegerField()
    attacker_hits = serializers.IntegerField()
    defender_hits = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Dice Rolled: {obj['attacker_roll']} / {obj['defender_roll']}. Hits assigned: {obj['attacker_hits']} to Attacker, {obj['defender_hits']} to Defender"


class PieceRemovalLogDetailsSerializer(serializers.Serializer):
    faction = serializers.CharField()
    piece_type = serializers.CharField()  # 'Warrior', 'Token', 'Building'
    clearing_number = serializers.IntegerField()
    count = serializers.IntegerField(default=1)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        faction = Faction(obj["faction"]).label
        piece = obj["piece_type"]
        count = obj.get("count", 1)
        if count > 1:
            if piece.lower().endswith("s"):
                pass  # Already plural or ends in s (like Roost -> Roosts is done below, but 'Bases' would be here)
            elif piece.lower() == "warrior":
                piece = "Warriors"
            elif piece.lower() == "token":
                piece = "Tokens"
            elif piece.lower() == "building":
                piece = "Buildings"
            elif piece.lower().endswith("y"):
                piece = piece[:-1] + "ies"
            else:
                piece += "s"
        return f"Removed {count} {faction} {piece} in clearing {obj['clearing_number']}"


# ==================
# FACTORIES
# ==================
def log_turn(
    game: Game, player: Player, turn_number: int, parent: GameLog | None = None
) -> GameLog:
    """Log the start of a player's turn."""
    serializer = TurnLogDetailsSerializer(data={"turn_number": turn_number})
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.TURN,
        details=serializer.validated_data,
        parent=parent,
    )


def log_phase(
    game: Game, player: Player, phase: str, parent: GameLog | None = None
) -> GameLog:
    """Log the start of a specific turn phase (Birdsong, Daylight, Evening)."""
    serializer = PhaseLogDetailsSerializer(data={"phase": phase})
    serializer.is_valid(raise_exception=True)

    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.PHASE,
        details=serializer.validated_data,
        parent=parent,
    )


def log_move(
    game: Game,
    player: Player,
    origin_number: int,
    dest_number: int,
    warriors_moved: int,
    parent: GameLog | None = None,
) -> GameLog:
    serializer = MoveLogDetailsSerializer(
        data={
            "origin_clearing_number": origin_number,
            "dest_clearing_number": dest_number,
            "warriors_moved": warriors_moved,
        }
    )
    serializer.is_valid(raise_exception=True)

    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOVE,
        details=serializer.validated_data,
        parent=parent,
    )


def log_craft(
    game: Game, player: Player, card: Card, parent: GameLog | None = None
) -> GameLog:
    serializer = CraftLogDetailsSerializer(data={"card": CardSerializer(card).data})
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.CRAFT,
        details=serializer.validated_data,
        parent=parent,
    )


def log_battle(
    game: Game,
    player: Player,
    clearing_number: int,
    defender_faction: str,
    battle_id: int | None = None,
    parent: GameLog | None = None,
) -> GameLog:
    serializer = BattleLogDetailsSerializer(
        data={
            "clearing_number": clearing_number,
            "attacker_faction": player.faction,
            "defender_faction": defender_faction,
            "battle_id": battle_id,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.BATTLE,
        details=serializer.validated_data,
        parent=parent,
    )


def log_draw(
    game: Game, player: Player, drawn_cards: list[Card], parent: GameLog | None = None
) -> GameLog:
    serializer = DrawLogDetailsSerializer(
        data={
            "cards": CardSerializer(drawn_cards, many=True).data,
            "count": len(drawn_cards),
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.DRAW,
        details=serializer.validated_data,
        parent=parent,
    )


def log_discard(
    game: Game, player: Player, card: Card, parent: GameLog | None = None
) -> GameLog:
    serializer = DiscardLogDetailsSerializer(data={"card": CardSerializer(card).data})
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.DISCARD,
        details=serializer.validated_data,
        parent=parent,
    )


def log_ambush(
    game: Game, player: Player, card: Card, parent: GameLog | None = None
) -> GameLog:
    serializer = AmbushLogDetailsSerializer(
        data={"card": CardSerializer(card).data, "faction": player.faction}
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.AMBUSH,
        details=serializer.validated_data,
        parent=parent,
    )


def log_dice_roll(
    game: Game,
    player: Player,
    attacker_roll: int,
    defender_roll: int,
    attacker_hits: int,
    defender_hits: int,
    parent: GameLog | None = None,
) -> GameLog:
    serializer = DiceRollLogDetailsSerializer(
        data={
            "attacker_roll": attacker_roll,
            "defender_roll": defender_roll,
            "attacker_hits": attacker_hits,
            "defender_hits": defender_hits,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.DICE_ROLL,
        details=serializer.validated_data,
        parent=parent,
    )


def log_piece_removal(
    game: Game,
    player: Player,
    faction: str,
    piece_type: str,
    clearing_number: int,
    count: int = 1,
    parent: GameLog | None = None,
) -> GameLog:
    serializer = PieceRemovalLogDetailsSerializer(
        data={
            "faction": faction,
            "piece_type": piece_type,
            "clearing_number": clearing_number,
            "count": count,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.PIECE_REMOVAL,
        details=serializer.validated_data,
        parent=parent,
    )


def get_current_turn_log(game: Game, player: Player) -> GameLog | None:
    return (
        GameLog.objects.filter(game=game, player=player, log_type=LogType.TURN)
        .order_by("-created_at")
        .first()
    )


def get_current_phase_log(game: Game, player: Player) -> GameLog | None:
    return (
        GameLog.objects.filter(game=game, player=player, log_type=LogType.PHASE)
        .order_by("-created_at")
        .first()
    )


def get_active_phase_log(game: Game) -> GameLog | None:
    from game.queries.general import get_current_player

    try:
        player = get_current_player(game)
        return get_current_phase_log(game, player)
    except Exception:
        return None


def get_battle_log(game: Game, battle_id: int) -> GameLog | None:
    return GameLog.objects.filter(
        game=game, log_type=LogType.BATTLE, details__battle_id=battle_id
    ).last()


def get_serializer_data(log: GameLog, details: dict, request=None):
    if log.log_type == LogType.TURN:
        if "turn_number" not in details:
            details["turn_number"] = 1
        return TurnLogDetailsSerializer(details).data
    if log.log_type == LogType.PHASE:
        if "phase" not in details:
            details["phase"] = "Unknown"
        return PhaseLogDetailsSerializer(details).data
    if log.log_type == LogType.MOVE:
        if "origin_clearing_id" in details and "origin_clearing_number" not in details:
            details["origin_clearing_number"] = details.pop("origin_clearing_id", None)
        if "dest_clearing_id" in details and "dest_clearing_number" not in details:
            details["dest_clearing_number"] = details.pop("dest_clearing_id", None)
        return MoveLogDetailsSerializer(details).data
    if log.log_type == LogType.CRAFT:
        return CraftLogDetailsSerializer(details).data
    if log.log_type == LogType.BATTLE:
        if "clearing_id" in details and "clearing_number" not in details:
            details["clearing_number"] = details.pop("clearing_id", None)
        return BattleLogDetailsSerializer(details).data
    if log.log_type == LogType.AMBUSH:
        return AmbushLogDetailsSerializer(details).data
    if log.log_type == LogType.DICE_ROLL:
        return DiceRollLogDetailsSerializer(details).data
    if log.log_type == LogType.PIECE_REMOVAL:
        return PieceRemovalLogDetailsSerializer(details).data
    if log.log_type == LogType.DRAW:
        data = dict(details)
        if request and hasattr(request, "user"):
            if log.player and log.player.user != request.user:
                data = DrawLogDetailsSerializer.get_redacted_details(data)
        return DrawLogDetailsSerializer(data).data
    if log.log_type == LogType.DISCARD:
        return DiscardLogDetailsSerializer(details).data
    return None
