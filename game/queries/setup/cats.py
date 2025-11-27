from game.models.cats.buildings import CatBuildingTypes
from game.models.cats.setup import CatsSimpleSetup
from game.models.cats.tokens import CatKeep
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import Clearing, Player


def validate_timing(player: Player, cat_setup_step: CatsSimpleSetup.Steps):
    """checks that we are in catssetup step and the specified setup step"""
    game_setup = GameSimpleSetup.objects.get(game=player.game)
    if game_setup.status != GameSimpleSetup.GameSetupStatus.CATS_SETUP:
        raise ValueError("Not Cat's setup turn")
    cat_setup = CatsSimpleSetup.objects.get(player=player)
    if cat_setup.step != cat_setup_step:
        raise ValueError(f"Wrong step. Current step: {cat_setup.step}")


def validate_building_type(player: Player, building_type: CatBuildingTypes):
    """checks that the building type has not been placed yet"""
    cat_setup = CatsSimpleSetup.objects.get(player=player)
    placed_field_mapper = {
        CatBuildingTypes.WORKSHOP: "workshop_placed",
        CatBuildingTypes.SAWMILL: "sawmill_placed",
        CatBuildingTypes.RECRUITER: "recruiter_placed",
    }
    if getattr(cat_setup, placed_field_mapper[building_type]):
        raise ValueError(f"Building ({building_type.value}) has already been placed")


def validate_keep_is_here_or_adjacent(cat_player: Player, clearing: Clearing):
    """checks that the keep is here or adjacent to the clearing"""
    try:
        keep = CatKeep.objects.get(player=cat_player)
    except CatKeep.DoesNotExist:
        raise ValueError("No keep belongs to this player")
    adjacent = keep.clearing.connected_clearings.filter(pk=clearing.pk).exists()
    if not adjacent and clearing.pk != keep.clearing.pk:
        raise ValueError("Clearing is not adjacent to the keep or in the same clearing")
