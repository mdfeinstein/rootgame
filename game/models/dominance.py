from django.db import models
from game.models.game_models import Game, Card, Player


class DominanceSupplyEntry(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game", "card"],
                name="unique_dominance_supply_entry",
            )
        ]


class ActiveDominanceEntry(models.Model):
    player = models.OneToOneField(
        Player, on_delete=models.CASCADE, related_name="active_dominance"
    )
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
