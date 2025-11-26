from django.db import transaction

from game.models import DeckEntry, Player, Suit, Warrior, WarriorSupplyEntry
from game.models.wa.buildings import WABase
from game.models.wa.player import SupporterStackEntry
from game.models.wa.tokens import WASympathy


# TODO: create warrior supply could be a general function. only number of warriors is different
@transaction.atomic
def create_wa_warrior_supply(player: Player):
    # create warriors
    warriors = [Warrior(player=player) for _ in range(10)]
    for warrior in warriors:
        warrior.save()
    # assign warriors to supply
    supply_entries = [
        WarriorSupplyEntry(player=player, warrior=warrior) for warrior in warriors
    ]
    WarriorSupplyEntry.objects.bulk_create(supply_entries)


@transaction.atomic
def create_sympathy_tokens(player: Player):
    # create sympathy tokens
    for i in range(10):
        WASympathy(player=player, clearing=None).save()


@transaction.atomic
def create_wa_buildings(player: Player):
    """create 1 fox, 1 bunny, 1 rabbit base"""
    bases = [
        WABase(player=player, building_slot=None, suit=Suit.RED),
        WABase(player=player, building_slot=None, suit=Suit.YELLOW),
        WABase(player=player, building_slot=None, suit=Suit.ORANGE),
    ]
    for base in bases:
        base.save()


@transaction.atomic
def draw_supporters(player: Player):
    """draw 3 supporters from deck into supporter stack"""
    # select top 3 cards from deck
    cards_in_deck = list(
        DeckEntry.objects.filter(game=player.game)[:3]
    )  # ordered by spot by default
    assert len(cards_in_deck) == 3, "not enough cards in deck during WA setup!"
    SupporterStackEntry.objects.bulk_create(
        [
            SupporterStackEntry(player=player, card=card_in_deck.card)
            for card_in_deck in cards_in_deck
        ]
    )
    # delete cards from deck
    DeckEntry.objects.filter(
        pk__in=[card_in_deck.pk for card_in_deck in cards_in_deck]
    ).delete()


def wa_setup(player: Player):
    create_wa_warrior_supply(player)
    create_sympathy_tokens(player)
    create_wa_buildings(player)
    draw_supporters(player)
