# suit enum
from enum import Enum
from django.db import models

# from game.models.game_models import Suit as SuitTextChoice


class Suit(models.TextChoices):
    # should this just inherit from models.textchoice? will need to test this
    RED = "r", "Fox"
    YELLOW = "y", "Rabbit"
    ORANGE = "o", "Mouse"
    WILD = "b", "Bird"

    # def convert_to_textchoice(self) -> SuitTextChoice:
    #     return SuitTextChoice(self.value[0])


# faction enum
class Faction(models.TextChoices):
    CATS = "ca", "Cats"
    BIRDS = "bi", "Birds"
    WOODLAND_ALLIANCE = "wa", "Woodland Alliance"


class ItemTypes(models.TextChoices):
    BOOTS = "0", "Boots"
    BAG = "1", "Bag"
    CROSSBOW = "2", "Crossbow"
    HAMMER = "3", "Hammer"
    SWORD = "4", "Sword"
    TEA = "5", "Tea"
    COIN = "6", "Coin"
