from django.db import models

from game.models import Player


class CatTurn(models.Model):
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
        birdsong = CatBirdsong.objects.create(turn=turn)
        daylight = CatDaylight.objects.create(turn=turn)
        evening = CatEvening.objects.create(turn=turn)
        print(f"created cat turn {turn.turn_number}")
        return turn


class CatBirdsong(models.Model):
    class CatBirdsongSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        PLACING_WOOD = "1", "Place wood"
        # ASYNC_FIELD_HOSPITALS = "2", "Async field hospitals"
        COMPLETED = "3", "Completed"

    step = models.CharField(
        max_length=1,
        choices=CatBirdsongSteps.choices,
        default=CatBirdsongSteps.NOT_STARTED,
    )
    turn = models.OneToOneField(
        CatTurn, on_delete=models.CASCADE, related_name="birdsong"
    )


class CatDaylight(models.Model):
    class CatDaylightSteps(models.TextChoices):
        CRAFTING = "1", "Crafting"
        ACTIONS = "2", "Actions"
        COMPLETED = "3", "Completed"

    step = models.CharField(
        max_length=1,
        choices=CatDaylightSteps.choices,
        default=CatDaylightSteps.CRAFTING,
    )
    actions_left = models.IntegerField(default=3)
    recruit_used = models.BooleanField(default=False)
    turn = models.OneToOneField(
        CatTurn, on_delete=models.CASCADE, related_name="daylight"
    )
    # tracks if one of the two march moves have been taken.
    midmarch = models.BooleanField(default=False)


class CatEvening(models.Model):
    class CatEveningSteps(models.TextChoices):
        # NOT_STARTED = "0", "Not Started"
        DRAWING = "1", "Drawing Cards"
        DISCARDING = "2", "Discarding Cards"
        COMPLETED = "3", "Completed"

    step = models.CharField(
        max_length=1,
        choices=CatEveningSteps.choices,
        default=CatEveningSteps.DRAWING,
    )
    cards_drawn = models.IntegerField(default=0)
    turn = models.OneToOneField(
        CatTurn, on_delete=models.CASCADE, related_name="evening"
    )
