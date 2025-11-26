from django.db import models
from game.models import Player


class BirdsSimpleSetup(models.Model):
    class Steps(models.TextChoices):
        PICKING_CORNER = "1", "Picking Corner"
        CHOOSING_LEADER = "2", "Choosing Leader"
        PENDING_CONFIRMATION = "3", "Pending Confirmation"
        COMPLETED = "4", "Completed"

    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    step = models.CharField(
        max_length=1,
        choices=Steps.choices,
        default=Steps.PICKING_CORNER,
    )
