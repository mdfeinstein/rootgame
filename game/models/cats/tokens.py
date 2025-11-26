from game.models import Token
from django.db import models


class CatWood(Token):
    pass
    # check if player is cats?


class CatKeep(Token):
    destroyed = models.BooleanField(default=False)
