from game.queries.general import validate_can_activate_dominance
from game.models import HandEntry
from game.models import Player, Card, Suit
from game.models.dominance import DominanceSupplyEntry, ActiveDominanceEntry
from game.transactions.general import discard_card_from_hand
from game.queries.general import is_phase
from game.models.game_models import Clearing, Game
from game.queries.general import determine_clearing_rule
from django.db import transaction


@transaction.atomic
def swap_dominance(
    player: Player,
    card_in_hand: HandEntry,
    dominance_card_in_supply: DominanceSupplyEntry,
):
    # Validate Phase (Daylight)
    if not is_phase(player, "Daylight"):
        raise ValueError("Must be in daylight to swap dominance.")
    # get cards
    card_to_spend = card_in_hand.card
    dominance_card = dominance_card_in_supply.card
    # Validate Suit Match

    if card_to_spend.suit != Suit.WILD and card_to_spend.suit != dominance_card.suit:
        raise ValueError("Card suit does not match dominance card.")

    # Discard spending card
    discard_card_from_hand(player, card_in_hand)

    # Move dominance card to hand
    HandEntry.objects.create(player=player, card=dominance_card)
    dominance_card_in_supply.delete()


@transaction.atomic
def activate_dominance(player: Player, card_in_hand: HandEntry):
    # Validate Score
    validate_can_activate_dominance(player)
    # Get Card
    card = card_in_hand.card

    # Validate Card is Dominance
    if not card.dominance:
        raise ValueError("Card is not a dominance card.")
    # Activate
    ActiveDominanceEntry.objects.create(player=player, card=card)
    # Remove from Hand (it is now "played" / "active")
    card_in_hand.delete()


def check_dominance_victory(player: Player):
    try:
        active_dominance = ActiveDominanceEntry.objects.get(player=player)
    except ActiveDominanceEntry.DoesNotExist:
        return

    suit = active_dominance.card.suit
    game = player.game

    if suit == Suit.WILD:  # Bird Dominance
        # Rule 2 opposite corners
        # Corners are 1, 2, 3, 4. Opposites: (1, 3), (2, 4).
        corners = [1, 2, 3, 4]
        ruled_corners = []
        for c_num in corners:
            try:
                clearing = Clearing.objects.get(game=game, clearing_number=c_num)
                ruler = determine_clearing_rule(clearing)
                if ruler == player:
                    ruled_corners.append(c_num)
            except Clearing.DoesNotExist:
                pass

        has_1_3 = 1 in ruled_corners and 3 in ruled_corners
        has_2_4 = 2 in ruled_corners and 4 in ruled_corners

        if has_1_3 or has_2_4:
            trigger_victory(player)

    else:  # Suit Dominance
        # Rule 3 clearings of the suit
        # Get all clearings of suit
        needed = 3
        count = 0
        suit_clearings = Clearing.objects.filter(game=game, suit=suit)
        for clearing in suit_clearings:
            if determine_clearing_rule(clearing) == player:
                count += 1

        if count >= needed:
            trigger_victory(player)


def trigger_victory(player: Player):
    game = player.game
    game.status = Game.GameStatus.COMPLETED
    # Set winner logic if exists
    game.save()
    # potentially log or notify
