from collections import Counter
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Building, Player, Suit
from game.models.moles.buildings import Citadel, Market
from game.errors import IllegalActionError


def get_all_unused_mole_buildings(player: Player) -> list[Building]:
    """Returns all citadels and markets on map that haven't been crafted with this turn."""
    citadels = list(
        Citadel.objects.filter(
            player=player, building_slot__isnull=False, crafted_with=False
        )
    )
    markets = list(
        Market.objects.filter(
            player=player, building_slot__isnull=False, crafted_with=False
        )
    )
    return citadels + markets


def get_craftable_clearing_options(player: Player) -> list[dict]:
    """Returns clearing options for crafting: clearing_number with suit label."""
    buildings = get_all_unused_mole_buildings(player)
    clearing_number_set = set()
    clearing_suit: dict[int, Suit] = {}
    for b in buildings:
        cn = b.building_slot.clearing.clearing_number
        clearing_number_set.add(cn)
        clearing_suit[cn] = Suit(b.building_slot.clearing.suit)
    options = [
        {"value": str(cn), "label": f"Clearing {cn} ({clearing_suit[cn]})"}
        for cn in clearing_number_set
    ]
    return options


def get_buildings_from_clearing_numbers(
    player: Player, clearing_numbers: list[int]
) -> list[Citadel | Market]:
    """Fetches unused (re. crafting) buildings from a list of clearing numbers.

    Raises IllegalActionError if a clearing has no unused building.
    """
    counts = Counter(clearing_numbers)
    buildings = []
    for cn, count in counts.items():
        available = list(
            Citadel.objects.filter(
                player=player,
                building_slot__clearing__clearing_number=cn,
                building_slot__isnull=False,
                crafted_with=False,
            )
        ) + list(
            Market.objects.filter(
                player=player,
                building_slot__clearing__clearing_number=cn,
                building_slot__isnull=False,
                crafted_with=False,
            )
        )
        if len(available) < count:
            raise IllegalActionError(f"Not enough unused buildings in clearing {cn}")
        buildings.extend(available[:count])
    return buildings


def validate_crafting_pieces_satisfy_requirements(
    player: Player, card: CardsEP, buildings: list
) -> bool:
    """Validates that the given buildings satisfy the card's crafting cost.

    Suit derived from building.building_slot.clearing.suit.
    Raises IllegalActionError if pieces don't satisfy card requirements.
    """
    suits_needed = card.value.cost
    if len(buildings) != len(suits_needed):
        raise IllegalActionError(
            f"Card requires {len(suits_needed)} crafting pieces, got {len(buildings)}"
        )

    if len(buildings) != len(set(b.id for b in buildings)):
        raise IllegalActionError("Duplicate crafting pieces provided")

    satisfied = [False for _ in suits_needed]
    for building in buildings:
        if building.crafted_with:
            raise IllegalActionError(
                "A building has already been used for crafting this turn"
            )
        building_suit = Suit(building.building_slot.clearing.suit)
        matched = False
        first_wild_idx = None
        for i, suit_needed in enumerate(suits_needed):
            if satisfied[i]:
                continue
            if suit_needed.value == building_suit.value:
                satisfied[i] = True
                matched = True
                break
            elif suit_needed.value == Suit.WILD.value and first_wild_idx is None:
                first_wild_idx = i
        if not matched:
            if first_wild_idx is None:
                raise IllegalActionError(
                    f"Building in {building_suit} clearing does not satisfy any remaining requirement"
                )
            satisfied[first_wild_idx] = True

    return True
