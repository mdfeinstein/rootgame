from django.db import models

from game.models.game_models import Game


class GameSimpleSetup(models.Model):
    class GameSetupStatus(models.TextChoices):
        INITIAL_SETUP = "0", "Initial Setup"
        CATS_SETUP = "a", "Cats Setup"
        BIRDS_SETUP = "b", "Birds Setup"
        WOODLAND_ALLIANCE_SETUP = "c", "Woodland Alliance Setup"
        ALL_SETUP_COMPLETED = "2", "All Setup Completed"

    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="simple_setup"
    )
    status = models.CharField(
        max_length=1,
        choices=GameSetupStatus.choices,
        default=GameSetupStatus.INITIAL_SETUP,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game"],
                name="unique_game_setup_per_game",
            )
        ]
