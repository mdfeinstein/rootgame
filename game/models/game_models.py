from typing import cast
from django.db import models

# from django.contrib.auth.models import User

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.game_data.general.game_enums import ItemTypes

# from game.game_data.general.game_enums import Suit as SuitEnum


class Faction(models.TextChoices):
    CATS = "ca", "Cats"
    BIRDS = "bi", "Birds"
    WOODLAND_ALLIANCE = "wa", "Woodland Alliance"


class Suit(models.TextChoices):
    RED = "r", "Fox"
    YELLOW = "y", "Rabbit"
    ORANGE = "o", "Mouse"
    WILD = "b", "Bird"


class DayPhase(models.TextChoices):
    BIRDSONG = "0", "Birdsong"
    DAYLIGHT = "1", "Daylight"
    EVENING = "2", "Evening"


class Game(models.Model):
    class BoardMaps(models.TextChoices):
        AUTUMN = "0", "Autumn"
        WINTER = "1", "Winter"
        MOUNTAIN = "2", "Mountain"
        LAKE = "3", "Lake"

    boardmap = models.CharField(
        max_length=1,
        choices=BoardMaps.choices,
    )
    owner = models.ForeignKey("auth.User", on_delete=models.CASCADE)

    class GameStatus(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        STARTED = "1", "Started"
        SETUP_COMPLETED = "2", "Setup Completed"
        COMPLETED = "3", "Completed"

    status = models.CharField(
        max_length=1, choices=GameStatus.choices, default=GameStatus.NOT_STARTED
    )
    current_turn = models.PositiveSmallIntegerField(default=0)


class FactionChoiceEntry(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    faction = models.CharField(
        max_length=2,
        choices=Faction.choices,
    )
    chosen = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game", "faction"],
                name="unique_faction_choice_per_game",
            )
        ]


class Clearing(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    clearing_number = models.PositiveSmallIntegerField()
    connected_clearings = models.ManyToManyField("Clearing", related_name="+")
    water_connected_clearings = models.ManyToManyField("Clearing", related_name="+")
    suit = models.CharField(
        max_length=1,
        choices=Suit.choices,
    )


class BuildingSlot(models.Model):
    clearing = models.ForeignKey(Clearing, on_delete=models.CASCADE)
    building_slot_number = models.PositiveSmallIntegerField()


class Piece(models.Model):
    player = models.ForeignKey("Player", on_delete=models.CASCADE)


class Building(Piece):
    # null building spot: on player mat
    building_slot = models.ForeignKey(
        BuildingSlot,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        unique=True,
        related_name="building",
        default=None,
    )


class Ruin(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    # null building spot: removed from map
    building_slot = models.ForeignKey(
        "BuildingSlot", on_delete=models.CASCADE, null=True, blank=True
    )
    item = models.ForeignKey("Item", on_delete=models.CASCADE)


class Token(Piece):
    clearing = models.ForeignKey(
        Clearing, on_delete=models.CASCADE, null=True, blank=True
    )  # null clearing means token is on player mat


class CraftingPieceMixin(models.Model):
    crafted_with = models.BooleanField(
        default=False
    )  # tracks if used for crafting this turn

    class Meta:
        abstract = True


class Warrior(Piece):
    clearing = models.ForeignKey(
        Clearing, on_delete=models.CASCADE, null=True, blank=True
    )


class Card(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    suit = models.CharField(
        max_length=1,
        choices=Suit.choices,
        blank=False,
        null=False,
    )
    # look up array in other file will map card_id to card details.
    # card details dont belong here as that will be duplicated across many db entries
    card_type = models.CharField(
        max_length=50, choices=[(c.name, c.name) for c in CardsEP]
    )

    def save(self, *args, **kwargs):
        # auto-sync suit: card enums first value is letter, which is how it is saved
        self.suit = self.enum.value.suit.value[0]
        if not self.suit:
            raise ValueError("suit is blank")
        super().save(*args, **kwargs)

    @property
    def enum(self) -> CardsEP:
        return CardsEP[self.card_type]

    @property
    def title(self) -> str:
        return self.enum.value.title

    @property
    def craftable(self) -> bool:
        return self.enum.value.craftable

    @property
    def cost(
        self,
    ) -> list[str]:
        # convert list of enums to list of strings
        return [cast(str, suit.label) for suit in self.enum.value.cost]

    @property
    def text(self) -> str:
        return self.enum.value.text

    @property
    def item(self) -> ItemTypes | None:
        return self.enum.value.item

    @property
    def item_name(self) -> str:
        if self.item is None:
            return ""
        item_value = self.item
        return ItemTypes(item_value).label

    @property
    def crafted_points(self) -> int:
        return self.enum.value.crafted_points

    @property
    def ambush(self) -> bool:
        return self.enum.value.ambush

    @property
    def dominance(self) -> bool:
        return self.enum.value.dominance


class DeckEntry(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE, db_index=False)
    spot = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game", "spot"],
                name="unique_deck_spot",
            )
        ]
        ordering = ["spot"]
        indexes = [models.Index(fields=["game", "spot"])]

    def save(self, *args, **kwargs):
        if self.card.game != self.game:
            raise ValueError("card.game and game do not match")
        super().save(*args, **kwargs)


class DiscardPileEntry(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    spot = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game", "spot"],
                name="unique_discard_pile_spot",
            )
        ]
        ordering = ["spot"]

    def save(self, *args, **kwargs):
        if self.card.game != self.game:
            raise ValueError("card.game and game do not match")
        super().save(*args, **kwargs)

    @classmethod
    def create_from_card(cls, card: Card):
        spot = cls.objects.filter(game=card.game).count()
        entry = cls(game=card.game, card=card, spot=spot)
        entry.save()
        return entry


class Player(models.Model):
    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE
    )  # deleting a user will break the games
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="players")
    faction = models.CharField(max_length=2, choices=Faction.choices, null=True)
    score = models.IntegerField(default=0)
    turn_order = models.PositiveSmallIntegerField(
        default=None,
        null=True,
    )

    @property
    def faction_label(self) -> str:
        return Faction(self.faction).label


class WarriorSupplyEntry(models.Model):
    # warriors in the players supply.
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="warrior_supply_entries"
    )
    warrior = models.ForeignKey(Warrior, on_delete=models.CASCADE)


class Item(models.Model):
    class ItemTypes(models.TextChoices):
        BOOTS = "0", "Boots"
        BAG = "1", "Bag"
        CROSSBOW = "2", "Crossbow"
        HAMMER = "3", "Hammer"
        SWORD = "4", "Sword"
        TEA = "5", "Tea"
        COIN = "6", "Coin"

    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    item_type = models.CharField(
        max_length=1,
        choices=ItemTypes.choices,
    )
    exhausted = models.BooleanField(default=False)


class CraftableItemEntry(models.Model):
    # items still available to craft.
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)


class CraftedItemEntry(models.Model):
    # items crafted by players
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)


class CraftedCardEntry(models.Model):
    # cards crafted by players that sit in their playmat
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    card = models.ForeignKey(
        Card, on_delete=models.CASCADE, related_name="crafted_cards"
    )


class HandEntry(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
