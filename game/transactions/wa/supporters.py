from django.db import transaction

from game.errors.action_errors import IllegalActionError
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Card, DiscardPileEntry, Faction, Player
from game.models.wa.player import OfficerEntry, SupporterStackEntry
from game.queries.general import validate_player_has_card_in_hand
from game.queries.wa.supporters import can_add_supporter
from game.queries.wa.warriors import get_warriors_in_supply
from game.transactions.general import discard_card_from_hand, draw_card_from_deck


@transaction.atomic
def discard_supporters(player: Player, supporters: list[SupporterStackEntry]):
    """discards the given supporters"""
    for supporter in supporters:
        card = supporter.card
        DiscardPileEntry.create_from_card(card)
        supporter.delete()


def add_supporter(player: Player, card: Card):
    """adds a card to the players supporter stack
    If cannot add, card goes to discard pile
    """
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    if not can_add_supporter(player):
        DiscardPileEntry.create_from_card(card)
    else:
        SupporterStackEntry.objects.create(player=player, card=card)


@transaction.atomic
def draw_card_to_supporters(player: Player):
    """draws a card from the deck to the player's supporters"""
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    card = draw_card_from_deck(player)
    add_supporter(player, card)


@transaction.atomic
def mobilize_supporter(player: Player, card: CardsEP):
    """adds a supporter from hand to the player's stack, during mobilize action"""
    from game.models.wa.turn import WADaylight
    from game.queries.wa.turn import get_phase

    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    assert isinstance(get_phase(player), WADaylight), "Not day phase"
    card_in_hand = validate_player_has_card_in_hand(player, card)
    if not can_add_supporter(player):
        raise IllegalActionError(
            "Cannot add a supporter to the stack: no base and at limit"
        )

    add_supporter(player, card_in_hand.card)
    from game.serializers.logs.wa import log_wa_mobilize
    from game.serializers.logs.general import get_current_phase_log

    log_wa_mobilize(
        player.game,
        player,
        card_in_hand.card,
        parent=get_current_phase_log(player.game, player),
    )

    card_in_hand.delete()


@transaction.atomic
def add_officer(player: Player):
    """adds an officer to the player's officer box"""
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    reserve_warriors = get_warriors_in_supply(player)
    if not reserve_warriors.exists():
        raise IllegalActionError("No warriors in reserve")
    officer = OfficerEntry.objects.create(
        player=player, warrior=reserve_warriors.first()
    )


@transaction.atomic
def remove_officer(player: Player):
    """removes an officer from the player's officer box"""
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    officer = OfficerEntry.objects.filter(player=player).first()
    if officer is None:
        raise IllegalActionError("No officer in box")
    officer.warrior.clearing = None
    officer.warrior.save()
    officer.delete()
