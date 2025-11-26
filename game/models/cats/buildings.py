from enum import Enum
from django.db import models
from game.models import Building, CraftingPieceMixin


class CatBuilding(Building):
    class Meta:
        abstract = True


class Workshop(CatBuilding, CraftingPieceMixin):
    pass


class Sawmill(CatBuilding):
    used = models.BooleanField(default=False)


class Recruiter(CatBuilding):
    used = models.BooleanField(default=False)


class CatBuildingTypes(Enum):
    WORKSHOP = "Workshop"
    SAWMILL = "Sawmill"
    RECRUITER = "Recruiter"
