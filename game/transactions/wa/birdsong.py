from django.db import transaction

from game.models.game_models import (
    Building,
    Clearing,
    DiscardPileEntry,
    Player,
    Token,
    Warrior,
)
from game.models.wa.buildings import WABase
from game.models.wa.tokens import WASympathy
from game.queries.wa.supporters import get_sympathy_points, validate_revolt, validate_sympathy_spread
from game.transactions.general import place_piece_from_supply_into_clearing, place_warriors_into_clearing, raise_score
from game.transactions.removal import player_removes_building, player_removes_token, player_removes_warriors
from game.transactions.wa.supporters import discard_supporters, add_officer


@transaction.atomic
def place_sympathy(player: Player, clearing: Clearing):
    """places sympathy at the given clearing, scoring points"""
    to_score = get_sympathy_points(player)
    token = WASympathy.objects.filter(player=player, clearing=None).first()
    if token is None:
        raise ValueError("No sympathy token in the supply")
    if WASympathy.objects.filter(player=player, clearing=clearing).exists():
        raise ValueError("Player already has a sympathy token in this clearing")
    place_piece_from_supply_into_clearing(token, clearing)
    raise_score(player, to_score)


@transaction.atomic
def revolt(player: Player, clearing: Clearing):
    """revolts at the given clearing
    -- discards supporters
    -- removes all enemy pieces from the clearing (scoring points)
    -- places matching base in clearing
    -- gains troops equal to matching sympathetic clearings
    -- gains an officer
    """
    supporters = validate_revolt(player, clearing)
    discard_supporters(player, supporters)
    score_before = player.score
    pieces_destroyed = {}

    from game.serializers.logs.wa import log_wa_revolt
    from game.serializers.logs.general import get_current_phase_log

    revolt_log = log_wa_revolt(
        player.game,
        player,
        [],
        clearing.clearing_number,
        0,
        {},
        parent=get_current_phase_log(player.game, player),
    )

    for player_ in Player.objects.filter(game=player.game):
        if player_ != player:
            faction_label = player_.get_faction_display()
            count = Warrior.objects.filter(clearing=clearing, player=player_).count()
            if count > 0:
                player_removes_warriors(
                    clearing, player_, player_, count, parent=revolt_log, skip_log=True
                )
                key = f"{faction_label} Warrior"
                pieces_destroyed[key] = pieces_destroyed.get(key, 0) + count

            for token in Token.objects.filter(clearing=clearing, player=player_):
                from game.transactions.removal import get_piece_name

                token_label = f"{faction_label} {get_piece_name(token)}"
                player_removes_token(
                    player.game, token, player, parent=revolt_log, skip_log=True
                )
                pieces_destroyed[token_label] = pieces_destroyed.get(token_label, 0) + 1

            for building in Building.objects.filter(
                building_slot__clearing=clearing, player=player_
            ):
                from game.transactions.removal import get_piece_name

                building_label = f"{faction_label} {get_piece_name(building)}"
                player_removes_building(
                    player.game, building, player, parent=revolt_log, skip_log=True
                )
                pieces_destroyed[building_label] = pieces_destroyed.get(building_label, 0) + 1

    base = WABase.objects.get(player=player, suit=clearing.suit)
    place_piece_from_supply_into_clearing(base, clearing)

    matching_sympathy_count = WASympathy.objects.filter(
        player=player, clearing__suit=clearing.suit
    ).count()
    troops_in_supply = Warrior.objects.filter(player=player, clearing=None).count()
    place_warriors_into_clearing(
        player, clearing, min(matching_sympathy_count, troops_in_supply)
    )

    try:
        add_officer(player)
    except ValueError as e:
        if "No warriors in reserve" not in str(e):
            raise e

    player.refresh_from_db()
    points_scored = player.score - score_before

    from game.serializers.general_serializers import CardSerializer

    revolt_log.details["supporters_spent"] = CardSerializer(
        [s.card for s in supporters], many=True
    ).data
    revolt_log.details["points_scored"] = points_scored
    revolt_log.details["pieces_destroyed"] = pieces_destroyed
    revolt_log.save()


@transaction.atomic
def spread_sympathy(player: Player, clearing: Clearing):
    """spreads sympathy at the given clearing
    -- discards supporters
    -- places sympathy token
    -- score points
    """
    supporters = validate_sympathy_spread(player, clearing)
    score_before = player.score

    discard_supporters(player, supporters)
    place_sympathy(player, clearing)

    player.refresh_from_db()
    points_scored = player.score - score_before

    supporters_spent = [s.card for s in supporters]

    from game.serializers.logs.wa import log_wa_spread_sympathy
    from game.serializers.logs.general import get_current_phase_log

    log_wa_spread_sympathy(
        player.game,
        player,
        supporters_spent,
        clearing.clearing_number,
        points_scored,
        parent=get_current_phase_log(player.game, player),
    )


@transaction.atomic
def resolve_wa_base_removal(
    game,
    wa_player: Player,
    clearing: Clearing,
    building: Building,
    parent=None,
):
    """Rule 8.4.3: Discard all supporters matching its suit (including birds)
    Discard half of officers (rounded up)
    """
    from game.models.wa.player import SupporterStackEntry, OfficerEntry
    from game.models import Suit
    from game.serializers.logs.wa import (
        log_wa_supporters_lost,
        log_wa_officers_lost,
        log_wa_base_removed,
    )

    suit_to_match = building.suit
    wild_suit = Suit.WILD.value
    matching_supporters = SupporterStackEntry.objects.filter(
        player=wa_player, card__suit__in=[suit_to_match, wild_suit]
    )
    if matching_supporters.exists():
        log_wa_supporters_lost(
            game, wa_player, [s.card for s in matching_supporters], parent=parent
        )
        discard_supporters(wa_player, list(matching_supporters))

    officers = OfficerEntry.objects.filter(player=wa_player)
    officer_count = officers.count()
    if officer_count > 0:
        to_remove = (officer_count + 1) // 2
        log_wa_officers_lost(game, wa_player, to_remove, parent=parent)
        for officer in officers[:to_remove]:
            officer.warrior.clearing = None
            officer.warrior.save()
            officer.delete()

    log_wa_base_removed(
        game, wa_player, clearing.clearing_number, building.suit, parent=parent
    )


@transaction.atomic
def end_revolt_step(player: Player):
    from game.models.wa.turn import WABirdsong
    from game.queries.wa.turn import get_phase
    from game.transactions.wa.turn import next_step

    assert player.faction == "wa", "Not WA player"
    birdsong = get_phase(player)
    assert isinstance(birdsong, WABirdsong), "Not Birdsong phase"
    assert birdsong.step == WABirdsong.WABirdsongSteps.REVOLT, "Not Revolt step"
    next_step(player)


@transaction.atomic
def end_spread_sympathy_step(player: Player):
    from game.models.wa.turn import WABirdsong
    from game.queries.wa.turn import get_phase
    from game.transactions.wa.turn import next_step

    assert player.faction == "wa", "Not WA player"
    birdsong = get_phase(player)
    assert isinstance(birdsong, WABirdsong), "Not Birdsong phase"
    assert birdsong.step == WABirdsong.WABirdsongSteps.SPREAD_SYMPATHY, "Not Spread Sympathy step"
    next_step(player)
