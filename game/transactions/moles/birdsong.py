from django.db import transaction

from game.models.game_models import Player, Faction, Warrior
from game.models.moles.buildings import Citadel
from game.models.moles.burrow import Burrow
from game.models.moles.turn import MoleBirdsong
from game.queries.moles.turn import validate_step
from game.errors import UnavailableActionError


@transaction.atomic
def place_burrow_warriors(player: Player):
    """Place warriors in the burrow based on citadels on the board.
    Warriors placed = 1 + [0, 1, 3, 5][citadel_count]
    If not enough warriors in supply, place as many as available.
    """
    # Validate timing and faction
    if player.faction != Faction.MOLES:
        raise UnavailableActionError("This player is not Moles")
    validate_step(player, MoleBirdsong.MoleBirdsongSteps.PLACE_WARRIORS)

    # Count citadels on the board (clearing != null)
    citadels_on_board = Citadel.objects.filter(
        player=player, building_slot__isnull=False
    ).count()

    # Determine warriors to place using the formula: 1 + [0, 1, 3, 5][idx]
    warrior_increments = [0, 1, 3, 5]
    increment = warrior_increments[min(citadels_on_board, 3)]  # Cap at 3 citadels
    warriors_to_place_count = 1 + increment

    # Get burrow
    burrow = Burrow.objects.get(player=player)

    # Get available warriors from supply
    available_warriors = list(
        Warrior.objects.filter(player=player, clearing__isnull=True)[
            :warriors_to_place_count
        ]
    )

    # Place warriors in burrow
    for warrior in available_warriors:
        warrior.clearing = burrow
    Warrior.objects.bulk_update(available_warriors, ["clearing"])

    # Move to next step - import here to avoid circular imports
    from game.transactions.moles.turn import next_step

    next_step(player)
