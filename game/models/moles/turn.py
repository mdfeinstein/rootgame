from django.db import models
from game.models.game_models import Player


class MoleTurn(models.Model):
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
        MoleBirdsong.objects.create(turn=turn)
        MoleDaylight.objects.create(turn=turn)
        MoleEvening.objects.create(turn=turn)
        return turn


class MoleBirdsong(models.Model):
    class MoleBirdsongSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        PLACE_WARRIORS = "1", "Place Warriors"
        BEFORE_END = "z", "Before End"
        COMPLETED = "2", "Completed"

    turn = models.ForeignKey(MoleTurn, on_delete=models.CASCADE, related_name="birdsong")
    step = models.CharField(
        max_length=1,
        choices=MoleBirdsongSteps.choices,
        default=MoleBirdsongSteps.NOT_STARTED,
    )


class MoleDaylight(models.Model):
    class MoleDaylightSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        ACTIONS = "1", "Actions"
        MINISTER_ACTIONS = "2", "Minister Actions"
        SWAY_MINISTER = "3", "Sway Minister"
        BEFORE_END = "z", "Before End"
        COMPLETED = "4", "Completed"

    class BrigadierAction(models.TextChoices):
        NONE = "none", "None"
        BATTLE = "battle", "Battle"
        MOVE = "move", "Move"

    turn = models.ForeignKey(MoleTurn, on_delete=models.CASCADE, related_name="daylight")
    step = models.CharField(
        max_length=1,
        choices=MoleDaylightSteps.choices,
        default=MoleDaylightSteps.NOT_STARTED,
    )
    actions_left = models.IntegerField(default=2)
    brigadier_action = models.CharField(
        max_length=6,
        choices=BrigadierAction.choices,
        default=BrigadierAction.NONE,
    )


class MoleEvening(models.Model):
    class MoleEveningSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        PROCESS_REVEALED_CARDS = "1", "Process Revealed Cards"
        CRAFT = "2", "Craft"
        DRAW = "3", "Draw"
        DISCARD = "4", "Discard"
        BEFORE_END = "z", "Before End"
        COMPLETED = "5", "Completed"

    turn = models.ForeignKey(MoleTurn, on_delete=models.CASCADE, related_name="evening")
    step = models.CharField(
        max_length=1,
        choices=MoleEveningSteps.choices,
        default=MoleEveningSteps.NOT_STARTED,
    )
    cards_drawn = models.IntegerField(default=0)
