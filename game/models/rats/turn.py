from django.db import models
from game.models.game_models import Player
from game.models.enums import Suit


class RatsTurn(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    turn_number = models.PositiveSmallIntegerField()

    @classmethod
    def create_turn(cls, player: Player):
        turn_counts = cls.objects.filter(player=player).count()
        turn = cls(player=player, turn_number=turn_counts)
        turn.save()
        RatsBirdsong.objects.create(turn=turn)
        RatsDaylight.objects.create(turn=turn)
        RatsEvening.objects.create(turn=turn)
        return turn


class RatsBirdsong(models.Model):
    class Steps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        RAZE = "1", "Raze"
        SPREAD_MOB = "2", "Spread Mob"
        RECRUIT = "3", "Recruit"
        ANOINT = "4", "Anoint"
        CHOOSE_MOOD = "5", "Choose Mood"
        BEFORE_END = "z", "Before End"
        COMPLETED = "6", "Completed"

    turn = models.ForeignKey(RatsTurn, on_delete=models.CASCADE, related_name="birdsong")
    step = models.CharField(
        max_length=1,
        choices=Steps.choices,
        default=Steps.NOT_STARTED,
    )
    mob_die_suit = models.CharField(
        max_length=1,
        choices=Suit.choices,
        null=True,
        blank=True,
        default=None,
    )


class RatsDaylight(models.Model):
    class Steps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        CRAFT = "1", "Craft"
        COMMAND = "2", "Command"
        ADVANCE = "3", "Advance"
        BEFORE_END = "z", "Before End"
        COMPLETED = "4", "Completed"

    turn = models.ForeignKey(RatsTurn, on_delete=models.CASCADE, related_name="daylight")
    step = models.CharField(
        max_length=1,
        choices=Steps.choices,
        default=Steps.NOT_STARTED,
    )
    commands_used = models.IntegerField(default=0)
    prowess_used = models.IntegerField(default=0)


class RatsEvening(models.Model):
    class Steps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        INCITE = "1", "Incite"
        OPPRESS = "2", "Oppress"
        DRAW = "3", "Draw"
        DISCARD = "4", "Discard"
        BEFORE_END = "z", "Before End"
        COMPLETED = "5", "Completed"

    turn = models.ForeignKey(RatsTurn, on_delete=models.CASCADE, related_name="evening")
    step = models.CharField(
        max_length=1,
        choices=Steps.choices,
        default=Steps.NOT_STARTED,
    )
