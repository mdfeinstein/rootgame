from django.db import models
from game.models.game_models import Player


class Crown(models.Model):
    """
    A Moles-specific piece representing the Moles' Crown.
    Used to track which noble rank has been selected/used.
    """
    class CrownType(models.TextChoices):
        SQUIRE = "squire", "Squire"
        NOBLE = "noble", "Noble"
        LORD = "lord", "Lord"

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="crowns")
    type = models.CharField(
        max_length=10,
        choices=CrownType.choices,
        default=CrownType.SQUIRE,
    )
    used = models.BooleanField(default=False)
