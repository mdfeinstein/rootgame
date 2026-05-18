from django.db import models
from game.models import Building, CraftingPieceMixin


class MoleBuilding(Building):
    """Base class for Mole-specific buildings."""
    class Meta:
        abstract = True


class Citadel(MoleBuilding, CraftingPieceMixin):
    """
    A Moles-specific building used in their crafting system.
    Can be used as a crafting piece for card effects.
    """
    pass


class Market(MoleBuilding, CraftingPieceMixin):
    """
    A Moles-specific building used in their crafting system.
    Can be used as a crafting piece for card effects.
    """
    pass
