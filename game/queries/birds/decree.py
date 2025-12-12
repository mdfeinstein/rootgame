from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.player import DecreeEntry, Vizier
from game.models.birds.turn import BirdBirdsong
from game.models.game_models import Player, Suit
from game.queries.birds.turn import get_phase
from game.queries.general import validate_player_has_card_in_hand


def get_number_added_to_decree(player: Player) -> int:
    """returns the number of cards added to the player's decree this turn"""
    birdsong = get_phase(player)
    assert type(birdsong) == BirdBirdsong
    return birdsong.cards_added_to_decree


def get_bird_added_to_decree(player: Player) -> bool:
    """returns True if the player has added a bird card to the decree this turn"""
    birdsong = get_phase(player)
    assert type(birdsong) == BirdBirdsong
    return birdsong.bird_card_added_to_decree


def validate_card_to_decree(player: Player, card: CardsEP):
    """raises if the card cannot be added to the decree
    -- player doesn not have card in hand
    -- already two added (in which case we shouldn't be on this step still)
    -- a bird card was already added and we're trying to add another
    """
    validate_player_has_card_in_hand(player, card)
    if get_number_added_to_decree(player) >= 2:
        raise ValueError("Two cards already added to decree! Critical Error")
    if get_bird_added_to_decree(player) and card.value.suit == Suit.WILD:
        raise ValueError("Bird card already added to decree")


def get_decree_entry_to_use(
    player: Player, column: DecreeEntry.Column, suit: Suit
) -> DecreeEntry | Vizier:
    """returns the decree entry to use for the given column and suit
    raises if no suitable decree entry exists
    """
    decrees = DecreeEntry.objects.filter(column=column, player=player, fulfilled=False)
    viziers = Vizier.objects.filter(column=column, player=player, fulfilled=False)
    # if specific suit,use that.
    decree_to_use = decrees.filter(card__suit=suit).first()
    if decree_to_use is not None:
        return decree_to_use
    # if no specific suit, use a wild
    decree_to_use = decrees.filter(card__suit=Suit.WILD).first()
    if decree_to_use is not None:
        return decree_to_use
    # if no wild, use a vizier
    vizier_to_use = viziers.first()
    if vizier_to_use is not None:
        return vizier_to_use
    raise ValueError("No decree entry to use")
