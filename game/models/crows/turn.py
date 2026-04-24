from django.db import models
from game.models.game_models import Player

class CrowTurn(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    turn_number = models.PositiveSmallIntegerField()

    @classmethod
    def create_turn(cls, player: Player):
        turn_counts = cls.objects.filter(player=player).count()
        turn = cls(player=player, turn_number=turn_counts)
        turn.save()
        CrowBirdsong.objects.create(turn=turn)
        CrowDaylight.objects.create(turn=turn)
        CrowEvening.objects.create(turn=turn)
        return turn

class CrowBirdsong(models.Model):
    class CrowBirdsongSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        CRAFT = "1", "Craft"
        FLIP = "2", "Flip"
        RECRUIT = "3", "Recruit"
        BEFORE_END = "z", "Before End"
        COMPLETED = "4", "Completed"

    turn = models.ForeignKey(CrowTurn, on_delete=models.CASCADE, related_name="birdsong")
    step = models.CharField(
        max_length=1,
        choices=CrowBirdsongSteps.choices,
        default=CrowBirdsongSteps.NOT_STARTED,
    )

class CrowDaylight(models.Model):
    class CrowDaylightSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        ACTIONS = "1", "Actions"
        BEFORE_END = "z", "Before End"
        COMPLETED = "2", "Completed"

    turn = models.ForeignKey(CrowTurn, on_delete=models.CASCADE, related_name="daylight")
    step = models.CharField(
        max_length=1,
        choices=CrowDaylightSteps.choices,
        default=CrowDaylightSteps.NOT_STARTED,
    )
    actions_remaining = models.IntegerField(default=3)
    plots_placed = models.IntegerField(default=0)

class CrowEvening(models.Model):
    class CrowEveningSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        EXERT = "1", "Exert"
        DRAWING = "2", "Drawing"
        DISCARDING = "3", "Discarding"
        BEFORE_END = "z", "Before End"
        COMPLETED = "4", "Completed"

    turn = models.ForeignKey(CrowTurn, on_delete=models.CASCADE, related_name="evening")
    step = models.CharField(
        max_length=1,
        choices=CrowEveningSteps.choices,
        default=CrowEveningSteps.NOT_STARTED,
    )
    cards_drawn = models.IntegerField(default=0)
    exert_used = models.BooleanField(default=False)
