from rest_framework import serializers

from game.models.game_log import GameLog, LogType
from game.models.game_models import Game, Player, Card, Suit, Faction
from game.serializers.general_serializers import CardSerializer

# ==================
# SERIALIZERS
# ==================
class WARevoltLogDetailsSerializer(serializers.Serializer):
    supporters_spent = CardSerializer(many=True, required=False, allow_null=True)
    clearing_number = serializers.IntegerField(required=False)
    points_scored = serializers.IntegerField(required=False)
    pieces_destroyed = serializers.DictField(child=serializers.IntegerField(), required=False, allow_null=True)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        supporters_spent = obj.get('supporters_spent', [])
        counts = {}
        for card in supporters_spent:
            suit_label = card.get('suit', {}).get('label', 'Bird') if isinstance(card, dict) else card.get_suit_display()
            counts[suit_label] = counts.get(suit_label, 0) + 1
        spent_parts = [f"{count} {suit}" for suit, count in counts.items()]
        spent_str = " and ".join(spent_parts) if spent_parts else "0"
        
        clearing_number = obj.get('clearing_number', '?')
        base_text = f"Revolted in clearing {clearing_number}, spending {spent_str} supporters."
        
        destroyed_parts = []
        if 'pieces_destroyed' in obj and obj['pieces_destroyed']:
            pieces = obj['pieces_destroyed']
            for label, count in pieces.items():
                destroyed_parts.append(f"{count} {label}")
                
        if destroyed_parts:
            base_text += f" Destroyed {', '.join(destroyed_parts)}."
            
        points_scored = obj.get('points_scored', 0)
        if points_scored > 0:
            base_text += f" Scored {points_scored} VP."
            
        return base_text


class WASpreadSympathyLogDetailsSerializer(serializers.Serializer):
    supporters_spent = CardSerializer(many=True, required=False, allow_null=True)
    clearing_number = serializers.IntegerField(required=False)
    points_scored = serializers.IntegerField(required=False)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        supporters_spent = obj.get('supporters_spent', [])
        counts = {}
        for card in supporters_spent:
            suit_label = card.get('suit', {}).get('label', 'Bird') if isinstance(card, dict) else card.get_suit_display()
            counts[suit_label] = counts.get(suit_label, 0) + 1
        spent_parts = [f"{count} {suit}" for suit, count in counts.items()]
        spent_str = " and ".join(spent_parts) if spent_parts else "0"
        
        clearing_number = obj.get('clearing_number', '?')
        points_scored = obj.get('points_scored', 0)
        return f"Spread sympathy to clearing {clearing_number}, spending {spent_str} supporters and scoring {points_scored} VP."


class WAMobilizeLogDetailsSerializer(serializers.Serializer):
    card = CardSerializer(required=False, allow_null=True)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        card = obj.get('card') if isinstance(obj, dict) else getattr(obj, 'card', None)
        if not card:
            return "Mobilized a card to the supporter stack."
        
        title = card.get('title') if isinstance(card, dict) else getattr(card, 'title', 'Unknown Card')
        return f"Mobilized {title}."

    @classmethod
    def get_redacted_details(cls, details: dict) -> dict:
        redacted = dict(details)
        redacted.pop("card", None)
        return redacted


class WATrainLogDetailsSerializer(serializers.Serializer):
    card = CardSerializer(required=False, allow_null=True)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        card = obj.get('card') if isinstance(obj, dict) else getattr(obj, 'card', None)
        if card:
            title = card.get('title') if isinstance(card, dict) else getattr(card, 'title', 'Unknown Card')
        else:
            title = "Unknown Card"
        return f"Trained an officer with {title}."


class WAOrganizeLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField(required=False)
    points_scored = serializers.IntegerField(required=False)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        clearing_number = obj.get('clearing_number', '?')
        base = f"Organized a warrior in clearing {clearing_number}."
        points_scored = obj.get('points_scored', 0)
        if points_scored > 0:
            base += f" Scored {points_scored} VP."
        return base


class WAMilitaryOperationLogDetailsSerializer(serializers.Serializer):
    operation = serializers.CharField(required=False)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        operation = obj.get('operation', 'Unknown')
        return f"Performed {operation} military operation."


class WAOutrageLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    outrageous_player_faction = serializers.CharField()
    card_given = serializers.BooleanField()
    hand_shown = serializers.BooleanField()
    card = CardSerializer(required=False, allow_null=True)
    trigger_type = serializers.CharField(required=False, allow_blank=True)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        faction = Faction(obj['outrageous_player_faction']).label
        source = "move" if "move" in obj.get('trigger_type', '') else "removing sympathy"
        
        if obj.get('hand_shown'):
            return f"Outrage! {faction} had no matching card and showed hand for {source} in clearing {obj['clearing_number']}. (WA draws from deck)"
            
        if obj.get('card_given'):
            if obj.get('card'):
                # Handle Ambush labeling if needed? Card title is usually already rich if serialized right
                suit_label = obj['card']['suit']['label']
                title = obj['card']['title']
                # If it's an ambush, the title is usually "Ambush"
                return f"Outrage! {faction} handed over {title} ({suit_label}) for {source} in clearing {obj['clearing_number']}"
            else:
                return f"Outrage! {faction} handed over a card to WA for {source} in clearing {obj['clearing_number']}"
            
        return f"Outrage! {faction} triggered for {source} in clearing {obj['clearing_number']}"

    @classmethod
    def get_redacted_details(cls, details: dict) -> dict:
        redacted = dict(details)
        redacted.pop("card", None)
        return redacted

class WABaseRemovedLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    suit = serializers.CharField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        suit_label = dict(Suit.choices).get(obj['suit'], obj['suit'])
        return f"WA Base ({suit_label}) removed from clearing {obj['clearing_number']}."

class WAOfficersLostLogDetailsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Lost {obj['count']} officers due to base removal."

class WASupportersLostLogDetailsSerializer(serializers.Serializer):
    cards = CardSerializer(many=True)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        card_titles = ", ".join(c['title'] for c in obj['cards'])
        return f"Discarded {len(obj['cards'])} supporters: {card_titles}"

    @classmethod
    def get_redacted_details(cls, details: dict) -> dict:
        redacted = dict(details)
        redacted.pop("cards", None)
        return redacted

# ==================
# FACTORIES
# ==================
def log_wa_revolt(game: Game, player: Player, supporters_spent: dict, clearing_number: int, points_scored: int, pieces_destroyed: dict, parent: GameLog | None = None) -> GameLog:
    serializer = WARevoltLogDetailsSerializer(instance={
        "supporters_spent": supporters_spent,
        "clearing_number": clearing_number,
        "points_scored": points_scored,
        "pieces_destroyed": pieces_destroyed,
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.WA_REVOLT, details=serializer.data, parent=parent
    )


def log_wa_spread_sympathy(game: Game, player: Player, supporters_spent: dict, clearing_number: int, points_scored: int, parent: GameLog | None = None) -> GameLog:
    serializer = WASpreadSympathyLogDetailsSerializer(instance={
        "supporters_spent": supporters_spent,
        "clearing_number": clearing_number,
        "points_scored": points_scored,
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.WA_SPREAD_SYMPATHY, details=serializer.data, parent=parent
    )


def log_wa_mobilize(game: Game, player: Player, card: Card, parent: GameLog | None = None) -> GameLog:
    serializer = WAMobilizeLogDetailsSerializer(instance={
        "card": card,
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.WA_MOBILIZE, details=serializer.data, parent=parent
    )


def log_wa_train(game: Game, player: Player, card: Card, parent: GameLog | None = None) -> GameLog:
    serializer = WATrainLogDetailsSerializer(instance={
        "card": card,
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.WA_TRAIN, details=serializer.data, parent=parent
    )


def log_wa_organize(game: Game, player: Player, clearing_number: int, points_scored: int, parent: GameLog | None = None) -> GameLog:
    serializer = WAOrganizeLogDetailsSerializer(instance={
        "clearing_number": clearing_number,
        "points_scored": points_scored,
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.WA_ORGANIZE, details=serializer.data, parent=parent
    )


def log_wa_military_operation(game: Game, player: Player, operation: str, parent: GameLog | None = None) -> GameLog:
    serializer = WAMilitaryOperationLogDetailsSerializer(instance={
        "operation": operation,
    })
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.WA_MILITARY_OPERATION, details=serializer.data, parent=parent
    )


def log_wa_outrage(game: Game, wa_player: Player, outrageous_player: Player, clearing_number: int, card_given: bool, hand_shown: bool, trigger_type: str = "", card=None, outrage_event=None, parent: GameLog | None = None) -> GameLog:
    serializer = WAOutrageLogDetailsSerializer(data={
        "clearing_number": clearing_number,
        "outrageous_player_faction": outrageous_player.faction,
        "card_given": card_given,
        "hand_shown": hand_shown,
        "trigger_type": trigger_type,
        "card": CardSerializer(card).data if card else None
    })
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game, 
        player=wa_player, 
        log_type=LogType.WA_OUTRAGE, 
        details=serializer.validated_data, 
        parent=parent,
        outrage_event=outrage_event
    )

def log_wa_base_removed(game: Game, player: Player, clearing_number: int, suit: str, parent: GameLog | None = None) -> GameLog:
    serializer = WABaseRemovedLogDetailsSerializer(data={
        "clearing_number": clearing_number,
        "suit": suit
    })
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.WA_BASE_REMOVED, details=serializer.validated_data, parent=parent
    )

def log_wa_officers_lost(game: Game, player: Player, count: int, parent: GameLog | None = None) -> GameLog:
    serializer = WAOfficersLostLogDetailsSerializer(data={
        "count": count
    })
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.WA_OFFICERS_LOST, details=serializer.validated_data, parent=parent
    )

def log_wa_supporters_lost(game: Game, player: Player, cards: list[Card], parent: GameLog | None = None) -> GameLog:
    serializer = WASupportersLostLogDetailsSerializer(data={
        "cards": CardSerializer(cards, many=True).data
    })
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.WA_SUPPORTERS_LOST, details=serializer.validated_data, parent=parent
    )

def get_serializer_data(log: GameLog, details: dict, request=None):
    if log.log_type == LogType.WA_REVOLT:
        return WARevoltLogDetailsSerializer(details).data
    if log.log_type == LogType.WA_SPREAD_SYMPATHY:
        return WASpreadSympathyLogDetailsSerializer(details).data
    if log.log_type == LogType.WA_MOBILIZE:
        data = dict(details)
        if request and hasattr(request, "user"):
            if log.player and log.player.user != request.user:
                data = WAMobilizeLogDetailsSerializer.get_redacted_details(data)
        return WAMobilizeLogDetailsSerializer(data).data
    if log.log_type == LogType.WA_TRAIN:
        return WATrainLogDetailsSerializer(details).data
    if log.log_type == LogType.WA_ORGANIZE:
        return WAOrganizeLogDetailsSerializer(details).data
    if log.log_type == LogType.WA_MILITARY_OPERATION:
        return WAMilitaryOperationLogDetailsSerializer(details).data
    if log.log_type == LogType.WA_OUTRAGE:
        data = dict(details)
        if request and hasattr(request, "user"):
            outrageous_player_faction = details.get("outrageous_player_faction")
            from game.models.game_models import Player
            outrageous_player = Player.objects.filter(game=log.game, faction=outrageous_player_faction).first()
            if (log.player and log.player.user != request.user) and (outrageous_player and outrageous_player.user != request.user):
                data = WAOutrageLogDetailsSerializer.get_redacted_details(data)
        return WAOutrageLogDetailsSerializer(data).data
    if log.log_type == LogType.WA_BASE_REMOVED:
        return WABaseRemovedLogDetailsSerializer(details).data
    if log.log_type == LogType.WA_OFFICERS_LOST:
        return WAOfficersLostLogDetailsSerializer(details).data
    if log.log_type == LogType.WA_SUPPORTERS_LOST:
        data = dict(details)
        if request and hasattr(request, "user"):
            if log.player and log.player.user != request.user:
                data = WASupportersLostLogDetailsSerializer.get_redacted_details(data)
        return WASupportersLostLogDetailsSerializer(data).data
    return None
