from game.models import Player, Suit
from django.db import models

from game.models.events.event import Event


# class CatPlayer(Player):

#     def save(self, *args, **kwargs):
#         self.faction = "ca"
#         super().save(*args, **kwargs)


class FieldHospitalEvent(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    troops_To_save = models.IntegerField(default=0)
    suit = models.CharField(max_length=1, choices=Suit.choices)
