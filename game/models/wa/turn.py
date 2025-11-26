from django.db import models

from game.models import Player


class WABirdsong(models.Model):
    class WABirdsongSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        REVOLT = "1", "Revolt"
        SPREAD_SYMPATHY = "2", "Spread Sympathy"
        COMPLETED = "3", "Completed"

    step = models.CharField(
        max_length=1,
        choices=WABirdsongSteps.choices,
    )


class WADaylight(models.Model):
    class WADaylightSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        CRAFTING = "1", "Crafting"
        MOBILIZING = "2", "Mobilizing"
        TRAINING = "3", "Training"
        COMPLETED = "4", "Completed"

    step = models.CharField(
        max_length=1,
        choices=WADaylightSteps.choices,
    )


class WAEvening(models.Model):
    class WAEveningSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        MILITARY_OPERATIONS = "1", "Military Operations"
        DRAWING = "2", "Drawing Cards"
        DISCARDING = "3", "Discarding Cards"
        COMPLETED = "4", "Completed"

    step = models.CharField(
        max_length=1,
        choices=WAEveningSteps.choices,
    )
    operations_perfomed = models.IntegerField(default=0)
    cards_drawn = models.IntegerField(default=0)


class WATurn(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    turn_number = models.PositiveSmallIntegerField()
    birdsong = models.ForeignKey(WABirdsong, on_delete=models.CASCADE)
    daylight = models.ForeignKey(WADaylight, on_delete=models.CASCADE)
    evening = models.ForeignKey(WAEvening, on_delete=models.CASCADE)
