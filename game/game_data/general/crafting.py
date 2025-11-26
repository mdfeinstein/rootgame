from game.models.birds.buildings import BirdRoost
from game.models.cats.buildings import Workshop
from game.models import Faction
from game.models.wa.tokens import WASympathy
from django.db import models

crafting_piece_models: dict[Faction, list[type[models.Model]]] = {
    Faction.CATS: [Workshop],
    Faction.BIRDS: [BirdRoost],
    Faction.WOODLAND_ALLIANCE: [WASympathy],
}
