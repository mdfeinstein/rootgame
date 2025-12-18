from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.events.event import EventType
from game.models.events.wa import OutrageEvent
from game.models.game_models import Clearing, Faction, Game, Player, Suit
from game.models.wa.tokens import WASympathy
from game.queries.current_action.events import get_current_event
from game.queries.general import validate_player_has_card_in_hand


def move_triggers_outrage(moving_player: Player, clearing: Clearing) -> bool:
    """
    Returns True if the player's movement into clearing would trigger an outrage
    To trggier outrage:
    -- player is not woodland alliance
    -- clearing has a sympathy token
    """
    if moving_player.faction == Faction.WOODLAND_ALLIANCE:
        return False
    try:
        wa_player = Player.objects.get(
            game=moving_player.game, faction=Faction.WOODLAND_ALLIANCE
        )
    except Player.DoesNotExist:
        return False
    # check if sympathy in clearing
    return WASympathy.objects.filter(player=wa_player, clearing=clearing).exists()


def validate_card_can_pay_outrage(outrage_event: OutrageEvent, card: CardsEP):
    """raises if card does not satisfy outrage event
    -- not in hand of player who needs to pay
    -- not the right suit or wild
    Returns hand entry if card is valid
    """
    # check that player has card in hand
    hand_entry = validate_player_has_card_in_hand(outrage_event.outrageous_player, card)
    # check that card is in the right suit or wild
    if card.value.suit != outrage_event.suit and card.value.suit != Suit.WILD:
        raise ValueError("Card is not in the right suit")
    return hand_entry


def get_current_outrage_event(game: Game) -> OutrageEvent:
    """returns the current outrage event"""
    event = get_current_event(game)
    if event is None:
        raise ValueError("No events")
    if event.type != EventType.OUTRAGE:
        raise ValueError("Not an outrage event")
    return OutrageEvent.objects.get(event=event)
