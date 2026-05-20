from django.db import models

from game.models.game_models import Item, Player


class CurrentMood(models.Model):
    class MoodType(models.TextChoices):
        BITTER = "bitter", "Bitter"
        GRANDIOSE = "grandiose", "Grandiose"
        JUBILANT = "jubilant", "Jubilant"
        LAVISH = "lavish", "Lavish"
        RELENTLESS = "relentless", "Relentless"
        ROWDY = "rowdy", "Rowdy"
        STUBBORN = "stubborn", "Stubborn"
        WRATHFUL = "wrathful", "Wrathful"

    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="mood")
    mood_type = models.CharField(max_length=10, choices=MoodType.choices)


class CommandItemEntry(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="command_items"
    )
    item = models.OneToOneField(Item, on_delete=models.CASCADE)


class ProwessItemEntry(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="prowess_items"
    )
    item = models.OneToOneField(Item, on_delete=models.CASCADE)


class RatsPlayerState(models.Model):
    """Persistent per-player state for the Rats faction."""

    player = models.OneToOneField(
        Player, on_delete=models.CASCADE, related_name="rats_state"
    )
    looting_declared = models.BooleanField(default=False)
