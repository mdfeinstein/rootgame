# suit enum
from enum import Enum

# from game.models.game_models import Suit as SuitTextChoice


class Suit(Enum):
    # should this just inherit from models.textchoice? will need to test this
    RED = "r", "Fox"
    YELLOW = "y", "Rabbit"
    ORANGE = "o", "Mouse"
    WILD = "b", "Bird"

    # def convert_to_textchoice(self) -> SuitTextChoice:
    #     return SuitTextChoice(self.value[0])


# faction enum
class Faction(Enum):
    CATS = "ca", "Cats"
    BIRDS = "bi", "Birds"
    WOODLAND_ALLIANCE = "wa", "Woodland Alliance"


class ItemTypes(Enum):
    BOOTS = "0", "Boots"
    BAG = "1", "Bag"
    CROSSBOW = "2", "Crossbow"
    HAMMER = "3", "Hammer"
    SWORD = "4", "Sword"
    TEA = "5", "Tea"
    COIN = "6", "Coin"
