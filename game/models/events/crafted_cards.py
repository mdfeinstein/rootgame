from django.db import models
from game.models.events.event import Event
from game.models.game_models import CraftedCardEntry

class InformantsEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="informants"
    )
    crafted_card_entry = models.ForeignKey(
        CraftedCardEntry, on_delete=models.CASCADE, related_name="informants_events"
    )
