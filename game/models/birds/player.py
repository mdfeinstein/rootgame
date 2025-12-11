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
    # indicates if this decree entry has been used this turn
    fulfilled = models.BooleanField(default=False)

    class Meta:
        ordering = ["column", "card__suit"]


class Vizier(models.Model):
    class Column(models.TextChoices):
        RECRUIT = "R", "Recruit"
        MOVE = "M", "Move"
        BATTLE = "B", "Battle"
        BUILD = "U", "Build"

    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    column = models.CharField(max_length=1, choices=Column.choices)
    fulfilled = models.BooleanField(default=False)

    class Meta:
        ordering = ["column"]

    @classmethod
    def create_viziers(cls, player: Player):
        """creates viziers for the player dependent on the active leader"""
        leader = BirdLeader.objects.get(player=player, active=True)
        match leader.leader:
            case BirdLeader.BirdLeaders.BUILDER:
                cls.objects.create(player=player, column=cls.Column.RECRUIT)
                cls.objects.create(player=player, column=cls.Column.MOVE)
            case BirdLeader.BirdLeaders.CHARISMATIC:
                cls.objects.create(player=player, column=cls.Column.RECRUIT)
                cls.objects.create(player=player, column=cls.Column.BATTLE)
            case BirdLeader.BirdLeaders.COMMANDER:
                cls.objects.create(player=player, column=cls.Column.MOVE)
                cls.objects.create(player=player, column=cls.Column.BATTLE)
            case BirdLeader.BirdLeaders.DESPOT:
                cls.objects.create(player=player, column=cls.Column.MOVE)
                cls.objects.create(player=player, column=cls.Column.BUILD)
