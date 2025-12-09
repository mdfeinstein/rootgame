from game.models.cats.buildings import CatBuildingTypes
from django.apps import apps

from game.models.cats.tokens import CatWood
from game.models.game_models import Clearing, Player
from game.queries.general import determine_clearing_rule

scoring_after_placement = (
    {  # idx: [0 on board (before placement), 1 on board,... 6 on board] val: score
        CatBuildingTypes.SAWMILL: [0, 1, 2, 3, 4, 5],
        CatBuildingTypes.WORKSHOP: [0, 2, 2, 3, 4, 5],
        CatBuildingTypes.RECRUITER: [0, 1, 2, 3, 3, 4],
    }
)

wood_cost = [0, 1, 2, 3, 3, 4]  # idx is how many on board before placement, val is cost


def buildings_on_board(player: Player, building_type: CatBuildingTypes) -> int:
    """returns the number of buildings of the given type on the board"""
    # use enum value to access the correct model
    building_model = apps.get_model("game", building_type.value)
    return building_model.objects.filter(
        player=player, building_slot__isnull=False
    ).count()


def get_wood_cost(player: Player, building_type: CatBuildingTypes) -> int | None:
    """returns the cost of placing a building of the given type on the board
    returns None if no building of that type is in the supply
    """
    buildings_out = buildings_on_board(player, building_type)
    if buildings_out == 6:
        return None
    return wood_cost[buildings_out]


def get_score_after_placement(
    player: Player, building_type: CatBuildingTypes
) -> int | None:
    """returns the score of placing a building of the given type on the board
    returns None if no building of that type is in the supply
    """
    buildings_out = buildings_on_board(player, building_type)
    if buildings_out == 6:
        return None
    return scoring_after_placement[building_type][buildings_out]


def get_usable_wood_for_building(
    player: Player, building_type: CatBuildingTypes, clearing: Clearing
) -> list[CatWood] | None:
    """given a building to build, checks rule of clearings to see if there is enough connected wood to build it.
    If not enough connected wood returns None.
    """
    required_wood = get_wood_cost(player, building_type)
    if required_wood is None:  # no building of that type in supply
        raise ValueError(f"No building of that type in supply: {building_type.value}")
    # algo: add intended clearing to the stack. set for rulership island, set for unruled. if node in either set, pop off and continue .if ruled, add to rulership set,
    # add to result list, add its children to the stack and pop off. if unruled, add to unruled set and pop off.
    wood_tokens = []
    ruled_set = set()
    visited = set()
    clearing_stack = [clearing]
    while len(clearing_stack) > 0:
        clearing = clearing_stack.pop()
        if clearing in visited:
            continue
        visited.add(clearing)

        if determine_clearing_rule(clearing) == player:
            ruled_set.add(clearing)
        for connected_clearing in clearing.connected_clearings.all():
            if connected_clearing in visited:
                # not sure if this second check is needed, but unclear how the order of traversal may make the first check insufficient
                continue
            clearing_stack.append(connected_clearing)

    # tally up wood tokens in ruled sets
    for clearing_ in ruled_set:
        wood_in_clearing = CatWood.objects.filter(clearing=clearing_)
        wood_tokens.extend(wood_in_clearing)

    return wood_tokens if len(wood_tokens) >= required_wood else None
