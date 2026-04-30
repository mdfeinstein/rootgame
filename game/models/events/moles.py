from django.db import models

from game.models.events.event import Event


class PriceOfFailureEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="price_of_failure"
    )
