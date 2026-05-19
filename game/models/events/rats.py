from django.db import models

from game.models.events.event import Event, EventType
from game.models.game_models import Player


class HoardTooFullEvent(models.Model):
    class Track(models.TextChoices):
        COMMAND = "command", "Command"
        PROWESS = "prowess", "Prowess"

    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="hoard_too_full"
    )
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="hoard_too_full_events"
    )
    track = models.CharField(max_length=10, choices=Track.choices)

    @classmethod
    def create(cls, player: Player, track: "HoardTooFullEvent.Track") -> "HoardTooFullEvent":
        event = Event.objects.create(
            game=player.game, type=EventType.HOARD_TOO_FULL
        )
        return cls.objects.create(event=event, player=player, track=track)
