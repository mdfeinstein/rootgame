from django.db import models

from game.models.events.event import Event
from game.models.game_models import Player


class TurmoilEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="turmoil"
    )
    new_leader_chosen = models.BooleanField(default=False)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="turmoil")
