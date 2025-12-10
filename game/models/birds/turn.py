from django.db import models
from game.models import Player


class BirdTurn(models.Model):
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
        birdsong = BirdBirdsong.objects.create(turn=turn)
        daylight = BirdDaylight.objects.create(turn=turn)
        evening = BirdEvening.objects.create(turn=turn)
        return turn


class BirdBirdsong(models.Model):
    class BirdBirdsongSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        EMERGENCY_DRAWING = "1", "Emergency drawing"
        ADD_TO_DECREE = "2", "Add to Decree"
        EMERGENCY_ROOSTING = "3", "Emergency roosting"
        COMPLETED = "4", "Completed"

    turn = models.ForeignKey(
        BirdTurn, on_delete=models.CASCADE, related_name="birdsong"
    )
    step = models.CharField(
        max_length=1,
        choices=BirdBirdsongSteps.choices,
        default=BirdBirdsongSteps.NOT_STARTED,
    )
    cards_drawn = models.IntegerField(default=0)
    cards_added_to_decree = models.IntegerField(default=0)
    bird_card_added_to_decree = models.BooleanField(default=False)


class BirdDaylight(models.Model):
    class BirdDaylightSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        CRAFTING = "1", "Crafting"
        RECRUITING = "2", "Recruiting"
        MOVING = "3", "Moving"
        BATTLING = "4", "Battling"
        BUILDING = "5", "Building"
        COMPLETED = "6", "Completed"
        # turmoil steps
        HUMILIATE = "a", "Humiliate"
        PURGE = "b", "Purge"
        DEPOSE = "c", "Depose"

    turn = models.ForeignKey(
        BirdTurn, on_delete=models.CASCADE, related_name="daylight"
    )
    step = models.CharField(
        max_length=1,
        choices=BirdDaylightSteps.choices,
        default=BirdDaylightSteps.NOT_STARTED,
    )
    # decree model will track which cards have been used


class BirdEvening(models.Model):
    class BirdEveningSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        SCORING = "1", "Scoring"
        DRAWING = "2", "Drawing Cards"
        DISCARDING = "3", "Discarding Cards"
        COMPLETED = "4", "Completed"

    turn = models.ForeignKey(BirdTurn, on_delete=models.CASCADE, related_name="evening")
    step = models.CharField(
        max_length=1,
        choices=BirdEveningSteps.choices,
        default=BirdEveningSteps.NOT_STARTED,
    )
    cards_drawn = models.IntegerField(default=0)
