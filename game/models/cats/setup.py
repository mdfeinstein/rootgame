import django.db.models as models
from game.models import Player


class CatsSimpleSetup(models.Model):
    class Steps(models.TextChoices):
        PICKING_CORNER = "1", "Picking Corner"
        PLACING_BUILDINGS = "2", "Placing Buildings"
        PENDING_CONFIRMATION = "3", "Pending Confirmation"
        COMPLETED = "4", "Completed"

    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    step = models.CharField(
        max_length=1,
        choices=Steps.choices,
        default=Steps.PICKING_CORNER,
    )
    recruiter_placed = models.BooleanField(default=False)
    sawmill_placed = models.BooleanField(default=False)
    workshop_placed = models.BooleanField(default=False)

    # TODO: constrain one setup per player
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player"],
                name="unique_setup_per_player",
            )
        ]
