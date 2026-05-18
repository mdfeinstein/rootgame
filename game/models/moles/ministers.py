from django.db import models
from game.models.game_models import Player


class Minister(models.Model):
    """
    Moles-specific piece representing one of nine unique ministers.
    Ministers are organized by rank: Squires, Nobles, and Lords.
    """
    class MinisterName(models.TextChoices):
        MARSHAL = "marshal", "Marshal"
        CAPTAIN = "captain", "Captain"
        FOREMOLE = "foremole", "Foremole"
        BRIGADIER = "brigadier", "Brigadier"
        MAYOR = "mayor", "Mayor"
        BANKER = "banker", "Banker"
        DUCHESS_OF_MUD = "duchess", "Duchess of Mud"
        EARL_OF_STONE = "earl", "Earl of Stone"
        BARON_OF_DIRT = "baron", "Baron of Dirt"

    class MinisterRank(models.TextChoices):
        SQUIRE = "squire", "Squire"
        NOBLE = "noble", "Noble"
        LORD = "lord", "Lord"

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="ministers")
    name = models.CharField(
        max_length=20,
        choices=MinisterName.choices,
    )
    swayed = models.BooleanField(default=False)
    used = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "name"],
                name="unique_minister_per_player",
            )
        ]

    @property
    def crown_type(self) -> str:
        """Returns the crown type (rank) for this minister."""
        squire_ministers = [
            self.MinisterName.MARSHAL,
            self.MinisterName.CAPTAIN,
            self.MinisterName.FOREMOLE,
        ]
        noble_ministers = [
            self.MinisterName.BRIGADIER,
            self.MinisterName.MAYOR,
            self.MinisterName.BANKER,
        ]
        lord_ministers = [
            self.MinisterName.DUCHESS_OF_MUD,
            self.MinisterName.EARL_OF_STONE,
            self.MinisterName.BARON_OF_DIRT,
        ]

        if self.name in squire_ministers:
            return self.MinisterRank.SQUIRE.value
        elif self.name in noble_ministers:
            return self.MinisterRank.NOBLE.value
        elif self.name in lord_ministers:
            return self.MinisterRank.LORD.value
        else:
            raise ValueError(f"Unknown minister name: {self.name}")
