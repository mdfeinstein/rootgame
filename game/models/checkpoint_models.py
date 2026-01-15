from django.db import models
from game.models.game_models import Game

class Checkpoint(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='checkpoints')
    gamestate = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

class Action(models.Model):
    checkpoint = models.ForeignKey(Checkpoint, on_delete=models.CASCADE, related_name='actions')
    action_number = models.PositiveIntegerField()
    transaction_name = models.CharField(max_length=255)
    args = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['action_number']
        constraints = [
            models.UniqueConstraint(fields=['checkpoint', 'action_number'], name='unique_action_order')
        ]
