from rest_framework import serializers
from game.models.game_log import GameLog, LogType
from game.models.game_models import Game, Player
from game.serializers.general_serializers import CardSerializer


# ==================
# SERIALIZERS
# ==================

class MolesSetupPickCornerLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Moles picked clearing {obj['clearing_number']} as their corner"


class MolesBirdsongPlaceWarriorsLogDetailsSerializer(serializers.Serializer):
    warriors_placed = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Placed {obj['warriors_placed']} warrior(s) in the Burrow"


class MolesBuildLogDetailsSerializer(serializers.Serializer):
    building_type = serializers.CharField()
    clearing_number = serializers.IntegerField()
    card = CardSerializer()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        building = obj["building_type"].capitalize()
        return f"Built a {building} in clearing {obj['clearing_number']} (revealed {obj['card']['title']})"


class MolesRecruitLogDetailsSerializer(serializers.Serializer):
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return "Recruited 1 warrior into the Burrow"


class MolesDigLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    card = CardSerializer()
    warriors_moved = serializers.IntegerField()
    tunnel_moved_from = serializers.IntegerField(allow_null=True)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        base = f"Dug a tunnel in clearing {obj['clearing_number']}, moved {obj['warriors_moved']} warrior(s) (discarded {obj['card']['title']})"
        if obj.get("tunnel_moved_from") is not None:
            base += f" — tunnel relocated from clearing {obj['tunnel_moved_from']}"
        return base


class MolesSwayMinisterLogDetailsSerializer(serializers.Serializer):
    minister_name = serializers.CharField()
    crown_type = serializers.CharField()
    score = serializers.IntegerField()
    cards = CardSerializer(many=True)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Swayed {obj['minister_name'].capitalize()} using {len(obj['cards'])} card(s) ({obj['crown_type']} crown) — gained {obj['score']} VP"


class MolesMinisterMarshalLogDetailsSerializer(serializers.Serializer):
    origin_clearing_number = serializers.IntegerField()
    dest_clearing_number = serializers.IntegerField()
    warriors_moved = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Marshal moved {obj['warriors_moved']} warrior(s) from clearing {obj['origin_clearing_number']} to {obj['dest_clearing_number']}"


class MolesMinisterCaptainLogDetailsSerializer(serializers.Serializer):
    clearing_number = serializers.IntegerField()
    defender_faction = serializers.CharField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        from game.models.game_models import Faction
        return f"Captain initiated battle in clearing {obj['clearing_number']} against {Faction(obj['defender_faction']).label}"


class MolesMinisterBankerLogDetailsSerializer(serializers.Serializer):
    cards = CardSerializer(many=True)
    score = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Banker scored {obj['score']} VP from {len(obj['cards'])} card(s)"


class MolesMinisterDuchessLogDetailsSerializer(serializers.Serializer):
    score = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        if obj['score'] > 0:
            return f"Duchess of Mud scored {obj['score']} VP — all tunnels on the map"
        return "Duchess of Mud used — tunnels still in supply, no VP scored"


class MolesMinisterBaronLogDetailsSerializer(serializers.Serializer):
    markets_on_map = serializers.IntegerField()
    score = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Baron of Dirt scored {obj['score']} VP ({obj['markets_on_map']} market(s) on map)"


class MolesMinisterEarlLogDetailsSerializer(serializers.Serializer):
    citadels_on_map = serializers.IntegerField()
    score = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Earl of Stone scored {obj['score']} VP ({obj['citadels_on_map']} citadel(s) on map)"


class MolesMinisterBrigadierLogDetailsSerializer(serializers.Serializer):
    action = serializers.CharField()
    action_number = serializers.IntegerField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Brigadier {obj['action']} (action {obj['action_number']} of 2)"


class MolesMinisterMayorLogDetailsSerializer(serializers.Serializer):
    copied_minister_name = serializers.CharField()
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Mayor copied {obj['copied_minister_name'].capitalize()}"


class MolesEveningProcessRevealedLogDetailsSerializer(serializers.Serializer):
    cards_returned = CardSerializer(many=True)
    cards_discarded = CardSerializer(many=True)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        return f"Revealed cards processed: {len(obj['cards_returned'])} returned to hand, {len(obj['cards_discarded'])} discarded (Wild)"


class MolesPriceOfFailureLogDetailsSerializer(serializers.Serializer):
    discarded_card = CardSerializer()
    unswayed_minister = serializers.CharField(allow_blank=True)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        if obj['unswayed_minister']:
            return f"Price of Failure: {obj['unswayed_minister'].capitalize()} unswayed, discarded {obj['discarded_card']['title']}"
        return f"Price of Failure: discarded {obj['discarded_card']['title']} (no eligible ministers)"


# ==================
# FACTORIES
# ==================

def log_moles_setup_pick_corner(
    game: Game, player: Player, clearing_number: int, parent=None
) -> GameLog:
    serializer = MolesSetupPickCornerLogDetailsSerializer(
        data={"clearing_number": clearing_number}
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_SETUP_PICK_CORNER,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_birdsong_place_warriors(
    game: Game, player: Player, warriors_placed: int, parent=None
) -> GameLog:
    serializer = MolesBirdsongPlaceWarriorsLogDetailsSerializer(
        data={"warriors_placed": warriors_placed}
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_BIRDSONG_PLACE_WARRIORS,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_build(
    game: Game, player: Player, building_type: str, clearing_number: int, card, parent=None
) -> GameLog:
    serializer = MolesBuildLogDetailsSerializer(
        data={
            "building_type": building_type,
            "clearing_number": clearing_number,
            "card": card,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_BUILD,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_recruit(game: Game, player: Player, parent=None) -> GameLog:
    serializer = MolesRecruitLogDetailsSerializer(data={})
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_RECRUIT,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_dig(
    game: Game,
    player: Player,
    clearing_number: int,
    card,
    warriors_moved: int,
    tunnel_moved_from: int | None = None,
    parent=None,
) -> GameLog:
    serializer = MolesDigLogDetailsSerializer(
        data={
            "clearing_number": clearing_number,
            "card": card,
            "warriors_moved": warriors_moved,
            "tunnel_moved_from": tunnel_moved_from,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_DIG,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_sway_minister(
    game: Game,
    player: Player,
    minister_name: str,
    crown_type: str,
    score: int,
    cards,
    parent=None,
) -> GameLog:
    serializer = MolesSwayMinisterLogDetailsSerializer(
        data={
            "minister_name": minister_name,
            "crown_type": crown_type,
            "score": score,
            "cards": cards,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_SWAY_MINISTER,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_minister_marshal(
    game: Game,
    player: Player,
    origin_clearing_number: int,
    dest_clearing_number: int,
    warriors_moved: int,
    parent=None,
) -> GameLog:
    serializer = MolesMinisterMarshalLogDetailsSerializer(
        data={
            "origin_clearing_number": origin_clearing_number,
            "dest_clearing_number": dest_clearing_number,
            "warriors_moved": warriors_moved,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_MINISTER_MARSHAL,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_minister_captain(
    game: Game,
    player: Player,
    clearing_number: int,
    defender_faction: str,
    parent=None,
) -> GameLog:
    serializer = MolesMinisterCaptainLogDetailsSerializer(
        data={
            "clearing_number": clearing_number,
            "defender_faction": defender_faction,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_MINISTER_CAPTAIN,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_minister_foremole(
    game: Game,
    player: Player,
    building_type: str,
    clearing_number: int,
    card,
    parent=None,
) -> GameLog:
    serializer = MolesBuildLogDetailsSerializer(
        data={
            "building_type": building_type,
            "clearing_number": clearing_number,
            "card": card,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_MINISTER_FOREMOLE,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_minister_banker(
    game: Game,
    player: Player,
    cards,
    score: int,
    parent=None,
) -> GameLog:
    serializer = MolesMinisterBankerLogDetailsSerializer(
        data={
            "cards": cards,
            "score": score,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_MINISTER_BANKER,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_minister_duchess(
    game: Game,
    player: Player,
    score: int,
    parent=None,
) -> GameLog:
    serializer = MolesMinisterDuchessLogDetailsSerializer(
        data={
            "score": score,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_MINISTER_DUCHESS,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_minister_baron(
    game: Game,
    player: Player,
    markets_on_map: int,
    score: int,
    parent=None,
) -> GameLog:
    serializer = MolesMinisterBaronLogDetailsSerializer(
        data={
            "markets_on_map": markets_on_map,
            "score": score,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_MINISTER_BARON,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_minister_earl(
    game: Game,
    player: Player,
    citadels_on_map: int,
    score: int,
    parent=None,
) -> GameLog:
    serializer = MolesMinisterEarlLogDetailsSerializer(
        data={
            "citadels_on_map": citadels_on_map,
            "score": score,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_MINISTER_EARL,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_minister_brigadier(
    game: Game,
    player: Player,
    action: str,
    action_number: int,
    parent=None,
) -> GameLog:
    serializer = MolesMinisterBrigadierLogDetailsSerializer(
        data={
            "action": action,
            "action_number": action_number,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_MINISTER_BRIGADIER,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_minister_mayor(
    game: Game,
    player: Player,
    copied_minister_name: str,
    parent=None,
) -> GameLog:
    serializer = MolesMinisterMayorLogDetailsSerializer(
        data={
            "copied_minister_name": copied_minister_name,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_MINISTER_MAYOR,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_evening_process_revealed(
    game: Game,
    player: Player,
    cards_returned,
    cards_discarded,
    parent=None,
) -> GameLog:
    serializer = MolesEveningProcessRevealedLogDetailsSerializer(
        data={
            "cards_returned": cards_returned,
            "cards_discarded": cards_discarded,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_EVENING_PROCESS_REVEALED,
        details=serializer.validated_data,
        parent=parent,
    )


def log_moles_price_of_failure(
    game: Game,
    player: Player,
    discarded_card,
    unswayed_minister: str = "",
    parent=None,
) -> GameLog:
    serializer = MolesPriceOfFailureLogDetailsSerializer(
        data={
            "discarded_card": discarded_card,
            "unswayed_minister": unswayed_minister,
        }
    )
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game,
        player=player,
        log_type=LogType.MOLES_PRICE_OF_FAILURE,
        details=serializer.validated_data,
        parent=parent,
    )


# ==================
# DISPATCHER
# ==================

def get_serializer_data(log, details, request=None):
    moles_serializers = {
        LogType.MOLES_SETUP_PICK_CORNER: MolesSetupPickCornerLogDetailsSerializer,
        LogType.MOLES_BIRDSONG_PLACE_WARRIORS: MolesBirdsongPlaceWarriorsLogDetailsSerializer,
        LogType.MOLES_BUILD: MolesBuildLogDetailsSerializer,
        LogType.MOLES_RECRUIT: MolesRecruitLogDetailsSerializer,
        LogType.MOLES_DIG: MolesDigLogDetailsSerializer,
        LogType.MOLES_SWAY_MINISTER: MolesSwayMinisterLogDetailsSerializer,
        LogType.MOLES_MINISTER_MARSHAL: MolesMinisterMarshalLogDetailsSerializer,
        LogType.MOLES_MINISTER_CAPTAIN: MolesMinisterCaptainLogDetailsSerializer,
        LogType.MOLES_MINISTER_FOREMOLE: MolesBuildLogDetailsSerializer,
        LogType.MOLES_MINISTER_BANKER: MolesMinisterBankerLogDetailsSerializer,
        LogType.MOLES_MINISTER_DUCHESS: MolesMinisterDuchessLogDetailsSerializer,
        LogType.MOLES_MINISTER_BARON: MolesMinisterBaronLogDetailsSerializer,
        LogType.MOLES_MINISTER_EARL: MolesMinisterEarlLogDetailsSerializer,
        LogType.MOLES_MINISTER_BRIGADIER: MolesMinisterBrigadierLogDetailsSerializer,
        LogType.MOLES_MINISTER_MAYOR: MolesMinisterMayorLogDetailsSerializer,
        LogType.MOLES_EVENING_PROCESS_REVEALED: MolesEveningProcessRevealedLogDetailsSerializer,
        LogType.MOLES_PRICE_OF_FAILURE: MolesPriceOfFailureLogDetailsSerializer,
    }
    serializer_class = moles_serializers.get(log.log_type)
    if serializer_class is None:
        return None
    return serializer_class(details).data
