from typing import Literal

from game.models.game_models import Player
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.enums import Suit
from game.models.game_models import BuildingSlot, Clearing, HandEntry, Player
from game.models.moles.buildings import Citadel, Market
from game.models.moles.crown import Crown
from game.models.moles.ministers import Minister
from game.models.moles.tokens import Tunnel
from game.errors import IllegalActionError, UnavailableActionError
from game.queries.general import (
    card_matches_clearing,
    determine_clearing_rule,
    available_building_slot,
    player_has_pieces_in_clearing,
    validate_player_has_card_in_hand,
)


def get_available_building_from_supply(
    player: Player, building_type: Literal["citadel", "market"]
) -> Citadel | Market:
    """Get an available building from supply, raise if none available.

    Args:
        player: The player
        building_type: "citadel" or "market"

    Returns:
        The building instance from supply

    Raises:
        IllegalActionError if no buildings of that type in supply
    """
    building_type = building_type.lower()
    if building_type == "citadel":
        building = Citadel.objects.filter(
            player=player, building_slot__isnull=True
        ).first()
        if building is None:
            raise IllegalActionError("No citadels left in supply")
        return building
    elif building_type == "market":
        building = Market.objects.filter(
            player=player, building_slot__isnull=True
        ).first()
        if building is None:
            raise IllegalActionError("No markets left in supply")
        return building
    else:
        raise IllegalActionError("Building Type not recognized")


def validate_card_in_hand(player: Player, card: CardsEP) -> HandEntry:
    """Validate player has card in hand, return the HandEntry.

    Raises:
        IllegalActionError if card not in hand
    """
    card_entry = HandEntry.objects.filter(
        player=player, card__card_type=card.name
    ).first()
    if card_entry is None:
        raise IllegalActionError(f"Card {card.value.title} not in hand")
    return card_entry


def validate_build_clearing(
    player: Player, clearing: Clearing, card: CardsEP
) -> BuildingSlot:
    """Validate clearing is valid for building (ruled, has slot, card matches).

    Returns:
        The BuildingSlot where the building can be placed

    Raises:
        IllegalActionError if clearing is not valid
    """
    # Check if clearing is ruled by this player
    if determine_clearing_rule(clearing) != player:
        raise IllegalActionError("Player must rule the clearing to build")

    # Check if clearing has available building slot
    slot = available_building_slot(clearing)
    if slot is None:
        raise IllegalActionError("No available building slots in clearing")
    # check that card is valid for the clearing
    if not card_matches_clearing(card, clearing):
        raise IllegalActionError("Card is not valid for clearing")
    return slot


def validate_dig_clearing(
    player: Player, clearing: Clearing, card: CardsEP
) -> Clearing:
    """Validate clearing for dig action (no tunnel present, card is valid for clearing).

    Raises:
        IllegalActionError if clearing already has a tunnel or card not valid for clearing
    """
    tunnel_exists = Tunnel.objects.filter(player=player, clearing=clearing).exists()
    if tunnel_exists:
        raise IllegalActionError("Clearing already has a tunnel")

    if not card_matches_clearing(card, clearing):
        raise IllegalActionError("Card is not valid for clearing")

    return clearing


def validate_tunnel_source_clearing(
    player: Player, source_clearing: Clearing | None
) -> Clearing | None:
    """Validate source clearing for tunnel move, if provided.

    Raises:
        IllegalActionError if source clearing doesn't have a player tunnel
    """
    if source_clearing is None:
        return None

    tunnel = Tunnel.objects.filter(player=player, clearing=source_clearing).first()
    if tunnel is None:
        raise IllegalActionError(
            f"No tunnel in source clearing {source_clearing.clearing_number}"
        )

    return source_clearing


def validate_foremole_clearing(player: Player, clearing: Clearing) -> BuildingSlot:
    """Validate clearing is valid for Foremole (ruled, has slot).

    Does not check card matching - Foremole's effect allows any card.

    Returns:
        The BuildingSlot where the building can be placed

    Raises:
        IllegalActionError if clearing is not valid
    """
    # Check if clearing is ruled by this player
    if determine_clearing_rule(clearing) != player:
        raise IllegalActionError("Player must rule the clearing to build")

    # Check if clearing has available building slot
    slot = available_building_slot(clearing)
    if slot is None:
        raise IllegalActionError("No available building slots in clearing")

    return slot


def validate_no_brigadier_in_progress(player: Player) -> None:
    """Validate that no Brigadier action is currently in progress.

    Args:
        player: The Moles player

    Raises:
        IllegalActionError if Brigadier action is in progress
    """
    from game.models.moles.turn import MoleDaylight
    from game.queries.moles.turn import get_phase

    phase = get_phase(player)
    if not isinstance(phase, MoleDaylight):
        raise UnavailableActionError("Not in Daylight phase")

    if phase.brigadier_action != MoleDaylight.BrigadierAction.NONE:
        raise IllegalActionError(
            "Cannot use another minister while Brigadier action is in progress. Use skip_brigadier to cancel."
        )


def validate_brigadier_action(phase, action_type) -> None:
    """Validate Brigadier action state and that we're not mixing actions.

    Args:
        phase: The MoleDaylight phase
        action_type: The action type being attempted (BATTLE or MOVE)

    Raises:
        IllegalActionError if trying to mix battle and move actions
    """
    from game.models.moles.turn import MoleDaylight

    if phase.brigadier_action == MoleDaylight.BrigadierAction.NONE:
        # First action, any type is allowed
        return

    if phase.brigadier_action == action_type:
        # Second action of same type is allowed
        return

    # Trying to mix actions
    raise IllegalActionError(
        f"Cannot mix Brigadier actions. Already doing {phase.brigadier_action}, cannot do {action_type}"
    )


def validate_banker_cards(player: Player, cards: list[CardsEP]) -> list[HandEntry]:
    """Validate all cards are in hand and of the same suit (Wild matches any).

    Args:
        player: The Moles player
        cards: List of cards to validate

    Returns:
        List of HandEntry objects for the cards

    Raises:
        IllegalActionError if any card not in hand or cards not same suit
    """
    if not cards:
        raise IllegalActionError("Must provide at least one card")

    card_entries = []
    for card in cards:
        entry = validate_card_in_hand(player, card)
        card_entries.append(entry)

    # Check all cards are same suit (Wild matches any suit)
    suits = [card.value.suit for card in cards]
    unique_suits = set(s for s in suits if s != "Wild")

    if len(unique_suits) > 1:
        raise IllegalActionError("All cards must be the same suit (Wild matches any)")

    return card_entries


def validate_minister_unused(
    player: Player, minister_name: Minister.MinisterName
) -> Minister:
    """Validate minister exists, is swayed, and has not been used this turn.

    Args:
        player: The Moles player
        minister_name: The MinisterName enum value

    Returns:
        The Minister instance

    Raises:
        IllegalActionError if minister not found or already used
    """
    minister = Minister.objects.filter(player=player, name=minister_name).first()
    if minister is None:
        raise IllegalActionError(f"Minister {minister_name} not found")

    if not minister.swayed:
        raise IllegalActionError(f"Minister {minister_name} not swayed")

    if minister.used:
        raise IllegalActionError(
            f"Minister {minister_name} has already been used this turn"
        )

    return minister


def validate_can_sway_minister(
    player: Player, minister: Minister.MinisterName
) -> Minister:
    """Validates that the given minister can be swayed,
    and returns the minister if so
    Raises if the minister cannot be swayed because:
    -- it is already swayed
    -- no available crown of the minister's tier
    """
    minister_instance = Minister.objects.get(player=player, name=minister)
    if minister_instance.swayed:
        raise IllegalActionError(f"Minister {minister} already swayed")
    if not Crown.objects.filter(
        player=player, type=minister_instance.crown_type, used=False
    ).exists():
        raise IllegalActionError(
            f"No crown of type {minister_instance.crown_type} available"
        )
    return minister_instance


def validate_cards_can_sway_minister(
    player: Player, minister: Minister.MinisterName, cards: list[CardsEP]
) -> list[HandEntry]:
    """Validates that the given cards can sway the given minister,
    and returns the hand entries if so
    """
    minister_instance = validate_can_sway_minister(player, minister)
    # validate number of cards sufficient for minister tier
    costs = {
        Crown.CrownType.SQUIRE: 2,
        Crown.CrownType.NOBLE: 3,
        Crown.CrownType.LORD: 4,
    }
    crown_type = Crown.CrownType(minister_instance.crown_type)
    if len(cards) != costs[crown_type]:
        raise IllegalActionError(
            f"Must provide {costs[crown_type]} cards to sway {minister}"
        )
    # validate cards in hand
    hand_entries = [validate_player_has_card_in_hand(player, card) for card in cards]
    # validate that each card revealed matches a clearing with moles pieces in it
    clearing_set: set[Clearing] = set()
    for card in cards:  # first pass: non-wild cards, since they are less flexible
        if card.value.suit == Suit.WILD:
            continue
        clearings = Clearing.objects.filter(game=player.game, suit=card.value.suit)
        found = False
        for clearing in clearings:
            if clearing in clearing_set:
                continue
            if player_has_pieces_in_clearing(player, clearing):
                clearing_set.add(clearing)
                found = True
                break
        if not found:
            raise IllegalActionError(
                f"{card.value.title} does not match any clearings with moles pieces in it"
            )
    for card in cards:  # second pass: wild cards,
        if card.value.suit != Suit.WILD:
            continue
        clearings = Clearing.objects.filter(
            game=player.game
        )  # all clearings match wild
        found = False
        for clearing in clearings:
            if clearing in clearing_set:
                continue
            if player_has_pieces_in_clearing(player, clearing):
                clearing_set.add(clearing)
                found = True
                break
        if not found:
            raise IllegalActionError(
                f"{card.value.title} does not match any clearings with moles pieces in it"
            )
    return hand_entries


def validate_cards_match_clearings(player: Player, cards: list[CardsEP]) -> bool:
    """Validate that cards match clearings with moles pieces (no repeats).

    Each card must match a clearing with moles pieces. No clearing can be matched twice.
    Used for incremental validation during card selection.

    Args:
        player: The Moles player
        cards: List of cards to validate

    Returns:
        True if cards are valid

    Raises:
        IllegalActionError if any card doesn't match a clearing with pieces or clears are reused
    """
    clearing_set: set[Clearing] = set()
    for card in cards:
        if card.value.suit == Suit.WILD:
            continue
        clearings = Clearing.objects.filter(game=player.game, suit=card.value.suit)
        found = False
        for clearing in clearings:
            if clearing in clearing_set:
                continue
            if player_has_pieces_in_clearing(player, clearing):
                clearing_set.add(clearing)
                found = True
                break
        if not found:
            raise IllegalActionError(
                f"{card.value.title} does not match any clearings with moles pieces in it"
            )
    for card in cards:
        if card.value.suit != Suit.WILD:
            continue
        clearings = Clearing.objects.filter(game=player.game)
        found = False
        for clearing in clearings:
            if clearing in clearing_set:
                continue
            if player_has_pieces_in_clearing(player, clearing):
                clearing_set.add(clearing)
                found = True
                break
        if not found:
            raise IllegalActionError(
                f"{card.value.title} does not match any clearings with moles pieces in it"
            )
    return True


def get_actions_remaining(player: Player) -> int:
    """Get the number of actions remaining in the current daylight phase.

    Args:
        player: The Moles player

    Returns:
        Number of actions remaining (0-2)
    """
    from game.models.moles.turn import MoleDaylight
    from game.queries.moles.turn import get_phase

    phase = get_phase(player)
    if isinstance(phase, MoleDaylight):
        return phase.actions_left
    return 0
