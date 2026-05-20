from game.models.game_models import Clearing, Player
from game.queries.general import (
    count_player_pieces_in_clearing,
    determine_clearing_rule,
    player_has_pieces_in_clearing,
)


def get_oppressed_clearing_count(player: Player) -> int:
    """Return the number of clearings eligible for Oppress scoring.

    A clearing qualifies when:
    - The Rats player rules it (determined by standard rulership logic).
    - No other player has any pieces in the clearing.

    (If no enemies are present and Rats have any pieces, they trivially rule;
    the explicit rule-check also handles edge cases like Soup Kitchens.)
    """
    game = player.game
    other_players = list(
        game.players.exclude(pk=player.pk)
    )
    count = 0
    for clearing in Clearing.objects.filter(game=game):
        if determine_clearing_rule(clearing) != player:
            continue
        if any(
            player_has_pieces_in_clearing(other, clearing)
            for other in other_players
        ):
            continue
        count += 1
    return count


def get_rowdy_draw_count(player: Player) -> int:
    """Return the number of cards to draw in Evening, factoring in Rowdy mood.

    Base: 1 card.
    Rowdy (coin): draw 1 more; if the Warlord's clearing has 3+ enemy pieces
    (any combination across all enemy factions), draw 2 more instead.
    """
    from game.models.rats.player import CurrentMood
    from game.queries.rats.pieces import get_warlord

    base = 1
    mood = CurrentMood.objects.filter(player=player).first()
    if mood is None or mood.mood_type != CurrentMood.MoodType.ROWDY:
        return base

    warlord = get_warlord(player)
    if warlord.clearing is None:
        # Warlord not deployed — Rowdy bonus still applies at minimum (+1)
        return base + 1

    enemy_pieces = sum(
        count_player_pieces_in_clearing(other, warlord.clearing)
        for other in player.game.players.exclude(pk=player.pk)
    )
    return base + (2 if enemy_pieces >= 3 else 1)
