from django.db import models

from game.models.events.event import Event
from game.models.game_models import Suit


class FieldHospitalEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="field_hospital"
    )
    troops_to_save = models.PositiveSmallIntegerField()
    suit = models.CharField(max_length=1, choices=Suit.choices)
