from django.db import models
from game.models.game_models import Game


class RemovalEventTracker(models.Model):
    """Tracks removal events to deduplicate Price of Failure triggers.

    At most one tracker exists per game at any time.
    """
    game = models.OneToOneField(Game, on_delete=models.CASCADE, related_name="removal_tracker")
    price_of_failure_triggered = models.BooleanField(default=False)
