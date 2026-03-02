from django.db import transaction
from game.models.game_models import Player, Clearing, HandEntry, Suit, Faction
from game.models.crows.tokens import PlotToken
from game.models.crows.exposure import ExposureRevealedCards, ExposureGuessedPlot
from game.queries.crows.exposure import can_attempt_exposure
from game.queries.general import player_has_pieces_in_clearing
from game.transactions.removal import player_removes_token

@transaction.atomic
def guess_exposure(
    player: Player,
    clearing: Clearing,
    hand_entry: HandEntry,
    plot_token_type: PlotToken.PlotType,
):
    """
    Enemy of crows guesses the facedown plot type using a card.
    """
    if not can_attempt_exposure(player):
        raise ValueError("Cannot attempt exposure at this time")

    game = player.game
    crows_player = Player.objects.filter(game=game, faction=Faction.CROWS).first()
    if not crows_player:
        raise ValueError("No Crows player in this game")

    plot_token = PlotToken.objects.filter(
        player=crows_player, clearing=clearing, is_facedown=True
    ).first()
    
    if not plot_token:
        raise ValueError("No facedown plot token in this clearing")

    if not player_has_pieces_in_clearing(player, clearing):
        raise ValueError("Player has no pieces in this clearing")

    card_suit = hand_entry.card.suit
    if card_suit != clearing.suit and card_suit != Suit.WILD:
        raise ValueError("Card suit does not match clearing suit")

    if hand_entry.player != player:
        raise ValueError("Card is not in player's hand")

    # Ensure we are comparing strings
    if str(plot_token.plot_type) == str(plot_token_type):
        ExposureRevealedCards.objects.create(
            player=player,
            card=hand_entry.card
        )
        player_removes_token(game, plot_token, player, is_exposure=True)
    else:
        hand_entry.player = crows_player
        hand_entry.save()
        
        ExposureGuessedPlot.objects.create(
            player=player,
            guessed_plot_type=plot_token_type,
            clearing=clearing
        )
