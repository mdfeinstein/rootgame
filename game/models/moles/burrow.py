from django.db import models
from game.models.game_models import Clearing, Player


class Burrow(Clearing):
    """
    A special clearing accessible only to the Moles player.
    Each Moles player has exactly one Burrow. It has no adjacencies to other clearings.
    """

    player = models.OneToOneField(
        Player, on_delete=models.CASCADE, related_name="burrow"
    )

    def save(self, *args, **kwargs):
        # Set clearing number to 0 (outside normal board range of 1-12)
        self.clearing_number = 0
        # Burrow has no suit, but Clearing requires suit
        # Use empty string as a placeholder
        self.suit = ""
        super().save(*args, **kwargs)
