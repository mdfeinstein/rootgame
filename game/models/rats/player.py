from django.db import models

from game.models.enums import ItemTypes
from game.models.game_models import Item, Player


class CurrentMood(models.Model):
    class MoodType(models.TextChoices):
        BITTER = "bitter", "Bitter"
        GRANDIOSE = "grandiose", "Grandiose"
        JUBILANT = "jubilant", "Jubilant"
        LAVISH = "lavish", "Lavish"
        RELENTLESS = "relentless", "Relentless"
        ROWDY = "rowdy", "Rowdy"
        STUBBORN = "stubborn", "Stubborn"
        WRATHFUL = "wrathful", "Wrathful"

    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="mood")
    mood_type = models.CharField(max_length=10, choices=MoodType.choices)


class CommandItemEntry(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="command_items"
    )
    item = models.OneToOneField(Item, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    item__item_type__in=[
                        ItemTypes.BOOTS,
                        ItemTypes.BAG,
                        ItemTypes.COIN,
                    ]
                ),
                name="command_item_type_valid",
            )
        ]


class ProwessItemEntry(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="prowess_items"
    )
    item = models.OneToOneField(Item, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    item__item_type__in=[
                        ItemTypes.HAMMER,
                        ItemTypes.SWORD,
                        ItemTypes.TEA,
                        ItemTypes.CROSSBOW,
                    ]
                ),
                name="prowess_item_type_valid",
            )
        ]
