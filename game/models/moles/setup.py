from django.db import models
from game.models import Player


class MolesSimpleSetup(models.Model):
    class Steps(models.TextChoices):
        PICKING_CORNER = "1", "Picking Corner"
        PENDING_CONFIRMATION = "2", "Pending Confirmation"
        COMPLETED = "3", "Completed"

    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    step = models.CharField(
        max_length=1,
        choices=Steps.choices,
        default=Steps.PICKING_CORNER,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player"],
                name="unique_moles_setup_per_player",
            )
        ]
