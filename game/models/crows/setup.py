import django.db.models as models
from game.models.game_models import Player


class CrowsSimpleSetup(models.Model):
    class Steps(models.TextChoices):
        WARRIOR_PLACE = "1", "Warrior Place"
        PENDING_CONFIRMATION = "2", "Pending Confirmation"
        COMPLETED = "3", "Completed"

    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    step = models.CharField(
        max_length=1,
        choices=Steps.choices,
        default=Steps.WARRIOR_PLACE,
    )
    fox_placed = models.BooleanField(default=False)
    rabbit_placed = models.BooleanField(default=False)
    mouse_placed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player"],
                name="unique_crows_setup_per_player",
            )
        ]
