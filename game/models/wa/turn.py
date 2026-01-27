from django.db import models

from game.models import Player


class WATurn(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    turn_number = models.PositiveSmallIntegerField()

    @classmethod
    def create_turn(cls, player: Player):
        """creates a new turn for the player"""

        turn_counts = cls.objects.filter(player=player).count()
        # create turn
        turn = cls(
            player=player,
            turn_number=turn_counts,
        )
        turn.save()
        # create phases
        birdsong = WABirdsong.objects.create(turn=turn)
        daylight = WADaylight.objects.create(turn=turn)
        evening = WAEvening.objects.create(turn=turn)
        return turn


class WABirdsong(models.Model):
    class WABirdsongSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        REVOLT = "1", "Revolt"
        SPREAD_SYMPATHY = "2", "Spread Sympathy"
        COMPLETED = "3", "Completed"

    turn = models.ForeignKey(WATurn, on_delete=models.CASCADE)
    step = models.CharField(
        max_length=1,
        choices=WABirdsongSteps.choices,
        default=WABirdsongSteps.NOT_STARTED,
    )


class WADaylight(models.Model):
    class WADaylightSteps(models.TextChoices):
        ACTIONS = "1", "Actions"
        COMPLETED = "2", "Completed"

    turn = models.ForeignKey(WATurn, on_delete=models.CASCADE)
    step = models.CharField(
        max_length=1,
        choices=WADaylightSteps.choices,
        default=WADaylightSteps.ACTIONS,
    )


class WAEvening(models.Model):
    class WAEveningSteps(models.TextChoices):
        MILITARY_OPERATIONS = "1", "Military Operations"
        DRAWING = "2", "Drawing Cards"
        DISCARDING = "3", "Discarding Cards"
        COMPLETED = "4", "Completed"

    turn = models.ForeignKey(WATurn, on_delete=models.CASCADE)
    step = models.CharField(
        max_length=1,
        choices=WAEveningSteps.choices,
        default=WAEveningSteps.MILITARY_OPERATIONS,
    )
    operations_perfomed = models.IntegerField(default=0)
    cards_drawn = models.IntegerField(default=0)
