from django.db import models

from game.models.game_models import Token, CraftingPieceMixin


class PlotToken(Token, CraftingPieceMixin):
    class PlotType(models.TextChoices):
        BOMB = "bomb", "Bomb"
        SNARE = "snare", "Snare"
        EXTORTION = "extortion", "Extortion"
        RAID = "raid", "Raid"

    plot_type = models.CharField(
        max_length=15,
        choices=PlotType.choices,
    )
    is_facedown = models.BooleanField(default=True)
