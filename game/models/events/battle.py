from django.db import models

from game.models.game_models import Clearing, Faction
from game.models.events.event import Event


class Battle(models.Model):
    class BattleSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        DEFENDER_AMBUSH_CHECK = "1", "Defender Ambush"
        ATTACKER_AMBUSH_CANCEL_CHECK = "2", "Attacker Ambush"
        ATTACKER_CHOOSE_AMBUSH_HITS = "3", "Attacker Chooses Ambush Hits"
        ROLL_DICE = "4", "Roll Dice"
        DEFENDER_CHOOSE_HITS = "5", "Defender Chooses Hits"
        ATTACKER_CHOOSE_HITS = "6", "Attacker Chooses Hits"
        COMPLETED = "7", "Completed"

    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="battle")
    attacker = models.CharField(max_length=2, choices=Faction.choices)
    defender = models.CharField(max_length=2, choices=Faction.choices)
    clearing = models.ForeignKey(Clearing, on_delete=models.CASCADE)
    step = models.CharField(
        max_length=1,
        choices=BattleSteps.choices,
        default=BattleSteps.NOT_STARTED,
    )
    defender_ambush = models.BooleanField(default=False)
    attacker_cancel_ambush = models.BooleanField(default=False)
    attacker_ambush_hits_taken = models.PositiveSmallIntegerField(default=0)
    attacker_ambush_hits_assigned = models.PositiveSmallIntegerField(default=0)
    defender_hits_taken = models.PositiveSmallIntegerField(default=0)
    defender_hits_assigned = models.PositiveSmallIntegerField(default=0)
    attacker_hits_taken = models.PositiveSmallIntegerField(default=0)
    attacker_hits_assigned = models.PositiveSmallIntegerField(default=0)
