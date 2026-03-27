from rest_framework import serializers
from game.models.game_log import GameLog, LogType
from game.models.game_models import Game, Player, Card
from game.serializers.general_serializers import CardSerializer
from game.models.birds.player import DecreeEntry

# ==================
# SERIALIZERS
# ==================
class BirdsAddToDecreeLogDetailsSerializer(serializers.Serializer):
    decree_entry = serializers.JSONField()
    text = serializers.SerializerMethodField()
    def get_text(self, obj):
        column_value = obj['decree_entry']['column']
        column_label = dict(DecreeEntry.Column.choices).get(column_value, column_value)
        card_title = obj['decree_entry']['card']['title']
        return f"Added {card_title} to the {column_label} decree"

class BirdsEmergencyRoostLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    text = serializers.SerializerMethodField()
    def get_text(self, obj):
        return f"Placed an emergency roost and 3 warriors in clearing {obj['clearing_number']}"

class BirdsDecreeActionLogDetailsSerializer(serializers.Serializer):
    action = serializers.CharField()
    clearing_number = serializers.IntegerField(required=False, allow_null=True)
    text = serializers.SerializerMethodField()
    def get_text(self, obj):
        if obj.get('clearing_number'):
            return f"Resolved {obj['action'].capitalize()} action in clearing {obj['clearing_number']}"
        return f"Resolved {obj['action'].capitalize()} action"

class BirdsScoreRoostsLogDetailsSerializer(serializers.Serializer):
    points = serializers.IntegerField()
    text = serializers.SerializerMethodField()
    def get_text(self, obj):
        return f"Scored {obj['points']} VP for Roosts"

class BirdsTurmoilLogDetailsSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, allow_null=True)
    points_lost = serializers.IntegerField()
    cards_lost = serializers.IntegerField()
    text = serializers.SerializerMethodField()
    def get_text(self, obj):
        prefix = f"Failed to complete {obj['action'].capitalize()} step!" if obj.get('action') else "Fell into Turmoil!"
        return f"{prefix} Lost {obj['points_lost']} VP and discarded {obj['cards_lost']} decree cards."

class BirdsNewLeaderLogDetailsSerializer(serializers.Serializer):
    leader = serializers.JSONField()

    text = serializers.SerializerMethodField()
    def get_text(self, obj):
        return f"Chose the {obj['leader']['leader_display']} as the new leader"

class BirdsSetupPickCornerLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    text = serializers.SerializerMethodField()
    def get_text(self, obj):
        return f"Placed initial Roost and 6 warriors in clearing {obj['clearing_number']}"

class BirdsSetupChooseLeaderLogDetailsSerializer(serializers.Serializer):
    leader = serializers.JSONField()

    text = serializers.SerializerMethodField()
    def get_text(self, obj):
        return f"Picked {obj['leader']['leader_display']} as starting leader"

# ==================
# FACTORIES
# ==================
def log_birds_add_to_decree(game: Game, player: Player, decree_entry: DecreeEntry, parent: GameLog | None = None) -> GameLog:
    from game.serializers.bird_serializers import BirdDecreeEntrySerializer
    serializer = BirdsAddToDecreeLogDetailsSerializer(instance={
        "decree_entry": BirdDecreeEntrySerializer(decree_entry).data
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.BIRDS_ADD_TO_DECREE, details=serializer.data, parent=parent
    )

def log_birds_emergency_roost(game: Game, player: Player, clearing_number: int, parent: GameLog | None = None) -> GameLog:
    serializer = BirdsEmergencyRoostLogDetailsSerializer(instance={
        "clearing_number": clearing_number
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.BIRDS_EMERGENCY_ROOST, details=serializer.data, parent=parent
    )

def log_birds_decree_action(game: Game, player: Player, action: str, clearing_number: int | None = None, parent: GameLog | None = None) -> GameLog:
    serializer = BirdsDecreeActionLogDetailsSerializer(instance={
        "action": action,
        "clearing_number": clearing_number
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.BIRDS_DECREE_ACTION, details=serializer.data, parent=parent
    )

def log_birds_score_roosts(game: Game, player: Player, points: int, parent: GameLog | None = None) -> GameLog:
    serializer = BirdsScoreRoostsLogDetailsSerializer(instance={
        "points": points
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.BIRDS_SCORE_ROOSTS, details=serializer.data, parent=parent
    )

def log_birds_turmoil(game: Game, player: Player, points_lost: int, cards_lost: int, action: str | None = None, parent: GameLog | None = None) -> GameLog:
    serializer = BirdsTurmoilLogDetailsSerializer(instance={
        "action": action,
        "points_lost": points_lost,
        "cards_lost": cards_lost
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.BIRDS_TURMOIL, details=serializer.data, parent=parent
    )

def log_birds_new_leader(game: Game, player: Player, leader: 'BirdLeader', parent: GameLog | None = None) -> GameLog:
    from game.serializers.bird_serializers import BirdLeaderSerializer
    serializer = BirdsNewLeaderLogDetailsSerializer(instance={
        "leader": BirdLeaderSerializer(leader).data
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.BIRDS_NEW_LEADER, details=serializer.data, parent=parent
    )

def log_birds_setup_pick_corner(game: Game, player: Player, clearing_number: int, parent: GameLog | None = None) -> GameLog:
    serializer = BirdsSetupPickCornerLogDetailsSerializer(instance={
        "clearing_number": clearing_number
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.BIRDS_SETUP_PICK_CORNER, details=serializer.data, parent=parent
    )

def log_birds_setup_choose_leader(game: Game, player: Player, leader: 'BirdLeader', parent: GameLog | None = None) -> GameLog:
    from game.serializers.bird_serializers import BirdLeaderSerializer
    serializer = BirdsSetupChooseLeaderLogDetailsSerializer(instance={
        "leader": BirdLeaderSerializer(leader).data
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.BIRDS_SETUP_CHOOSE_LEADER, details=serializer.data, parent=parent
    )


def get_serializer_data(log: GameLog, details: dict, request=None):
    if log.log_type == LogType.BIRDS_ADD_TO_DECREE:
        return BirdsAddToDecreeLogDetailsSerializer(details).data
    if log.log_type == LogType.BIRDS_EMERGENCY_ROOST:
        return BirdsEmergencyRoostLogDetailsSerializer(details).data
    if log.log_type == LogType.BIRDS_DECREE_ACTION:
        return BirdsDecreeActionLogDetailsSerializer(details).data
    if log.log_type == LogType.BIRDS_SCORE_ROOSTS:
        return BirdsScoreRoostsLogDetailsSerializer(details).data
    if log.log_type == LogType.BIRDS_TURMOIL:
        return BirdsTurmoilLogDetailsSerializer(details).data
    if log.log_type == LogType.BIRDS_NEW_LEADER:
        return BirdsNewLeaderLogDetailsSerializer(details).data
    if log.log_type == LogType.BIRDS_SETUP_PICK_CORNER:
        return BirdsSetupPickCornerLogDetailsSerializer(details).data
    if log.log_type == LogType.BIRDS_SETUP_CHOOSE_LEADER:
        return BirdsSetupChooseLeaderLogDetailsSerializer(details).data
    return None
