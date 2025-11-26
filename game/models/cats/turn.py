from django.db import models

from game.models import Player


class CatBirdsong(models.Model):
    class CatBirdsongSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        PLACE_WOOD = "1", "Place wood"
        ASYNC_FIELD_HOSPITALS = "2", "Async field hospitals"
        COMPLETED = "3", "Completed"

    step = models.CharField(
        max_length=1,
        choices=CatBirdsongSteps.choices,
    )


class CatDaylight(models.Model):
    class CatDaylightSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        CRAFTING = "1", "Crafting"
        ACTIONS = "2", "Actions"
        COMPLETED = "3", "Completed"

    step = models.CharField(
        max_length=1,
        choices=CatDaylightSteps.choices,
    )
    actions_left = models.IntegerField(default=3)
    recruit_used = models.BooleanField(default=False)


class CatEvening(models.Model):
    class CatEveningSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        DRAWING = "1", "Drawing Cards"
        DISCARDING = "2", "Discarding Cards"
        COMPLETED = "3", "Completed"

    step = models.CharField(
        max_length=1,
        choices=CatEveningSteps.choices,
    )
    cards_drawn = models.IntegerField(default=0)


class CatTurn(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    turn_number = models.PositiveSmallIntegerField()
    birdsong = models.ForeignKey(CatBirdsong, on_delete=models.CASCADE)
    daylight = models.ForeignKey(CatDaylight, on_delete=models.CASCADE)
    evening = models.ForeignKey(CatEvening, on_delete=models.CASCADE)
