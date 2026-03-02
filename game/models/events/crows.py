from django.db import models

from game.models.events.event import Event
from game.models.game_models import Clearing, Suit


class CrowRecruitEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="crow_recruit"
    )
    suit = models.CharField(max_length=1, choices=Suit.choices)
    recruited_clearings = models.ManyToManyField(Clearing, blank=True)

class CrowRaidEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="crow_raid"
    )
    remaining_clearings = models.ManyToManyField(Clearing, blank=True)
