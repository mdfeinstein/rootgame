from django.db import models

from game.models.game_models import Game


class EventType(models.TextChoices):
    """Event types."""

    BATTLE = "battle"
    FIELD_HOSPITAL = "field_hospital"
    TURMOIL = "turmoil"
    OUTRAGE = "outrage"


class Event(models.Model):
    """Base class for all events."""

    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=50, choices=EventType.choices)
    is_resolved = models.BooleanField(default=False)
