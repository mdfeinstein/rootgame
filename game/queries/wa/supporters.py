from game.models.game_models import Clearing, Faction, Player, Suit
from game.models.wa.buildings import WABase
from game.models.wa.player import SupporterStackEntry
from game.models.wa.tokens import WASympathy
from game.queries.general import warrior_count_in_clearing


def get_supporters(
    player: Player, clearing: Clearing, count: int
) -> list[SupporterStackEntry]:
    """returns the supporter stack entries needed
    for count entries of the clearing suit
    raises if player does not have enough supporters
    """
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    # get suited supporters
    suited = list(
        SupporterStackEntry.objects.filter(player=player, card__suit=clearing.suit)[
            :count
        ]
    )
    if len(suited) == count:
        return suited
    left_to_get = count - len(suited)
    # get wild supporters
    wild = list(
        SupporterStackEntry.objects.filter(player=player, card__suit=Suit.WILD)[
            :left_to_get
        ]
    )
    supporters = suited + wild
    if len(supporters) == count:
        return supporters
    # if we still don't have enough, raise error
    raise ValueError("Not enough supporters to revolt")


def has_enough_to_revolt(player: Player) -> bool:
    """returns True if player can theoretically revolt
    This does not give private information, only checks if he theoretically can
    -- player has at least two supporters
    -- player has at least one sympathy on the board
    """
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    # check supporters
    if not SupporterStackEntry.objects.filter(player=player).count() >= 2:
        return False
    # check if sympathy is on the board
    if not WASympathy.objects.filter(player=player, clearing__isnull=False).exists():
        return False
    return True


def validate_revolt(player: Player, clearing: Clearing) -> list[SupporterStackEntry]:
    """validates that player can revolt at the given clearing,
    and returns the supporter stack entries that would be used for the revolt
    -- player has a sympathy in that clearing
    -- player has at least two supporters that match the clearing
    -- player's matching base is not on the board yet
    Selected supporters should be exact suit if possible, wild if not
    """
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    # check clearing for sympathy
    sympathy = WASympathy.objects.filter(player=player, clearing=clearing).first()
    if sympathy is None:
        raise ValueError("No sympathy in that clearing")
    # check if matching base is on the board
    if WABase.objects.filter(
        player=player, suit=clearing.suit, building_slot__isnull=False
    ).exists():
        raise ValueError("Matching base is on the board")
    # get suited supporters
    suit = clearing.suit
    return get_supporters(player, suit, 2)


sympathy_cost = [1, 1, 1, 2, 2, 2, 3, 3, 3, 3]  # idx: num on board before placed
sympathy_points = [0, 1, 1, 1, 2, 2, 3, 4, 4, 4]


def has_enough_to_spread_sympathy(player: Player) -> bool:
    """returns True if player can theoretically spread sympathy
    This does not give private information, only checks if he theoretically can
    -- player has sympathy in reserve
    -- player has enough supporters to match current base cost
    """
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    # check if sympathy in reserve
    if not WASympathy.objects.filter(player=player, clearing__isnull=True).exists():
        return False
    # get supporter count
    supporter_count = SupporterStackEntry.objects.filter(player=player).count()
    sympathy_on_board = WASympathy.objects.filter(
        player=player, clearing__isnull=False
    ).count()
    current_cost = sympathy_cost[sympathy_on_board]
    print(f"supporter count: {supporter_count}, current cost: {current_cost}")
    return supporter_count >= current_cost


def get_sympathy_cost(player: Player, clearing: Clearing) -> int:
    """returns the cost of placing a sympathy token in the given clearing
    -- checks players sympathy on the board
    -- checks for martial law
    raises if this clearing already has a sympathy token
    """
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    # get number of sympathy tokens on the board
    sympathy_count = WASympathy.objects.filter(
        player=player, clearing__isnull=False
    ).count()
    # check if martial law is in effect
    martial_law: bool = False
    for player_ in Player.objects.filter(game=player.game):
        if player_ != player:
            three_warriors = warrior_count_in_clearing(player_, clearing) >= 3
            martial_law = martial_law or three_warriors
    # get cost
    martial_cost = 1 if martial_law else 0
    return sympathy_cost[sympathy_count] + martial_cost


def get_sympathy_points(player: Player) -> int:
    """returns the points of placing a sympathy token on the board"""
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    # get number of sympathy tokens on the board
    sympathy_count = WASympathy.objects.filter(
        player=player, clearing__isnull=False
    ).count()
    return sympathy_points[sympathy_count]


def validate_sympathy_spread(
    player: Player, clearing: Clearing
) -> list[SupporterStackEntry]:
    """validates that player can spread sympathy at the given clearing,
    and returns the supporter stack entries that would be used for the spread
    -- player doesn't have a sympathy in that clearing
    -- adjacent to other sympathies, if any on the board
    -- player has at enough supporters to spread to the clearing
    """
    assert player.faction == Faction.WOODLAND_ALLIANCE, "Not WA player"
    # check clearing for sympathy
    sympathy = WASympathy.objects.filter(player=player, clearing=clearing).first()
    if sympathy is not None:
        raise ValueError("Player already has a sympathy token in this clearing")
    # check adjacent sympathies
    has_adjacent_sympathies = WASympathy.objects.filter(
        player=player, clearing__isnull=False, clearing__connected_clearings=clearing
    ).exists()
    has_any_sympathies = WASympathy.objects.filter(
        player=player, clearing__isnull=False
    ).exists()
    if has_any_sympathies and not has_adjacent_sympathies:
        raise ValueError("No adjacent sympathies, but sympathy on the board")
    # get cost of placing sympathy
    cost = get_sympathy_cost(player, clearing)
    # get suited supporters
    return get_supporters(player, clearing, cost)
