from game.models import Building, Suit
from django.db import models


class WABase(Building):
    suit = models.CharField(max_length=1, choices=Suit.choices)
