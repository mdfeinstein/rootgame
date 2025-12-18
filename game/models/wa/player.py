from game.models import Player, Card, Warrior
from django.db import models


# class WAPlayer(Player):

#     def save(self, *args, **kwargs):
#         self.faction = "wa"
#         super().save(*args, **kwargs)


class SupporterStackEntry(models.Model):

    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="supporter_stack_entries"
    )
    card = models.ForeignKey(Card, on_delete=models.CASCADE)


class OfficerEntry(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="officer_entries"
    )
    warrior = models.ForeignKey(
        Warrior, on_delete=models.CASCADE, related_name="officer"
    )
    # tracks if officer used for military operations this turn
    used = models.BooleanField(default=False)
