from django.db import models
from game.models.game_models import Player, Clearing, Card
from game.models.crows.tokens import PlotToken

class ExposureRevealedCards(models.Model):
    """
    Stores cards revealed to the Crows via incorrect Exposure guesses.
    """
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="revealed_cards")
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    turn_number = models.IntegerField(default=0)

class ExposureGuessedPlot(models.Model):
    """
    Stores incorrect Exposure guesses made by other players against Crows plot tokens.
    """
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="guessed_plots")
    guessed_plot_type = models.CharField(max_length=20, choices=PlotToken.PlotType.choices)
    clearing = models.ForeignKey(Clearing, on_delete=models.CASCADE)
    turn_number = models.IntegerField(default=0)
