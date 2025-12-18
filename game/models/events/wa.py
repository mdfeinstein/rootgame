from django.db import models

from game.models.events.event import Event
from game.models.game_models import Player, Suit


class OutrageEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="outrage"
    )
    outraged_player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="outraged_events"
    )
    outrageous_player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="outrageous_events"
    )
    suit = models.CharField(max_length=1, choices=Suit.choices)
    card_given = models.BooleanField(default=False)
    hand_shown = models.BooleanField(default=False)
    # store shown hand data here
    hand = models.JSONField(default=dict, blank=True, null=True)
