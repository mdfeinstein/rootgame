from django.db import models
from game.models import Card, Player


# class BirdPlayer(Player):

#     def save(self, *args, **kwargs):
#         self.faction = "bi"
#         super().save(*args, **kwargs)


class BirdLeader(models.Model):
    class BirdLeaders(models.TextChoices):
        BUILDER = "0", "Builder"
        CHARISMATIC = "1", "Charismatic"
        COMMANDER = "2", "Commander"
        DESPOT = "3", "Despot"

    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    leader = models.CharField(
        max_length=1,
        choices=BirdLeaders.choices,
    )
    # available: hasn't been deposed yet
    available = models.BooleanField(default=True)
    active = models.BooleanField(default=False)


class DecreeEntry(models.Model):
    class Column(models.TextChoices):
        RECRUIT = "R", "Recruit"
        MOVE = "M", "Move"
        BATTLE = "B", "Battle"
        BUILD = "U", "Build"

    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="decree_entries",
    )
    column = models.CharField(max_length=1, choices=Column.choices)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)

    class Meta:
        ordering = ["column", "card__suit"]
