from django.db import models
from game.models.game_models import Player, Suit, Clearing
from game.models.events.event import Event


class FieldHospitalEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="field_hospital"
    )
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="field_hospital_events",
        null=True, blank=True
    )
    clearing = models.ForeignKey(Clearing, on_delete=models.CASCADE, null=True, blank=True)
    troops_to_save = models.PositiveSmallIntegerField()
    suit = models.CharField(max_length=1, choices=Suit.choices)
