from typing import Literal
from django.db import transaction

from game.errors.system_errors import InternalGameError
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.enums import Faction
from game.models.game_models import (
    Player,
    Clearing,
    Warrior,
    RevealedCardEntry,
)
from game.models.moles.turn import MoleDaylight
from game.models.moles.burrow import Burrow
from game.models.moles.tokens import Tunnel
from game.errors import IllegalActionError, UnavailableActionError
from game.queries.moles.turn import validate_step, get_phase
from game.queries.moles.daylight import (
    get_available_building_from_supply,
    validate_card_in_hand,
    validate_build_clearing,
    validate_dig_clearing,
    validate_tunnel_source_clearing,
)
from game.transactions.general import (
    move_warriors,
    place_piece_from_supply_into_clearing,
    discard_card_from_hand,
)
from game.transactions.battle import start_battle
from game.transactions.moles.turn import next_step
from game.serializers.general_serializers import CardSerializer
from game.serializers.logs.general import get_current_phase_log
from game.serializers.logs.moles import (
    log_moles_build,
    log_moles_recruit,
    log_moles_dig,
)


@transaction.atomic
def end_actions(player: Player):
    """End the Actions step and advance to the next step.

    Validates that it's the correct phase/step and the player is Moles.
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.ACTIONS)
    if player.faction != Faction.MOLES:
        raise UnavailableActionError("Not a Moles player")
    next_step(player)


@transaction.atomic
def decrement_actions(player: Player):
    """Decrement actions_left and advance to next step if 0."""
    validate_step(player, MoleDaylight.MoleDaylightSteps.ACTIONS)

    phase = get_phase(player)
    if not isinstance(phase, MoleDaylight):

        raise UnavailableActionError("Not in Daylight ACTIONS step")
    if phase.actions_left == 0:
        raise InternalGameError(
            "Actions left is 0 when decrement_actions called. shouldn't still be in the actions step."
        )
    phase.actions_left -= 1
    phase.save()

    if phase.actions_left == 0:
        next_step(player)


@transaction.atomic
def build(
    player: Player,
    card: CardsEP,
    building: Literal["citadel", "market"],
    clearing: Clearing,
):
    """Build a citadel or market using a card.

    Args:
        player: The Moles player
        card: The card being used
        building: "citadel" or "market"
        clearing: The clearing to build in

    Raises:
        IllegalActionError if card not in hand, clearing not ruled, etc.
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.ACTIONS)

    # Validate card is in hand
    card_entry = validate_card_in_hand(player, card)

    # Validate clearing is ruled and has building slot
    building_slot = validate_build_clearing(player, clearing, card)

    # Get building from supply
    building_instance = get_available_building_from_supply(player, building)

    # Place building
    building_instance.building_slot = building_slot
    building_instance.save()

    # Capture card before revealing (for logging)
    card_model = card_entry.card

    # Convert card to revealed
    RevealedCardEntry.hand_to_revealed(card_entry)

    # Log the action
    phase_log = get_current_phase_log(player.game, player)
    log_moles_build(
        player.game,
        player,
        building,
        clearing.clearing_number,
        CardSerializer(card_model).data,
        parent=phase_log,
    )

    # Decrement actions
    decrement_actions(player)


@transaction.atomic
def move(player: Player, origin: Clearing, target: Clearing, count: int):
    """Move warriors between clearings.

    Uses general move_warriors transaction which handles validations.
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.ACTIONS)

    move_warriors(player, origin, target, count)

    from game.serializers.logs.general import log_move
    log_move(
        player.game,
        player,
        origin.clearing_number,
        target.clearing_number,
        count,
        parent=get_current_phase_log(player.game, player),
    )

    # Decrement actions
    decrement_actions(player)


@transaction.atomic
def recruit(player: Player):
    """Place 1 warrior in the burrow from supply.

    Raises:
        IllegalActionError if no warriors in supply
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.ACTIONS)

    # Get a warrior from supply
    warrior = Warrior.objects.filter(player=player, clearing__isnull=True).first()
    if warrior is None:
        raise IllegalActionError("No warriors left in supply")

    # Get burrow and place warrior
    burrow = Burrow.objects.get(player=player)
    warrior.clearing = burrow
    warrior.save()

    # Log the action
    phase_log = get_current_phase_log(player.game, player)
    log_moles_recruit(player.game, player, parent=phase_log)

    # Decrement actions
    decrement_actions(player)


@transaction.atomic
def battle(player: Player, defender: Faction, clearing: Clearing):
    """Start a battle in a clearing.

    Uses start_battle from the battle transaction module.
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.ACTIONS)

    battle_obj = start_battle(
        player.game,
        attacker=Faction(player.faction),
        defender=Faction(defender),
        clearing=clearing,
    )

    from game.transactions.battle import log_battle_start
    log_battle_start(
        battle_obj,
        player,
        parent=get_current_phase_log(player.game, player),
    )

    # Decrement actions
    decrement_actions(player)


@transaction.atomic
def dig(
    player: Player,
    card: CardsEP,
    clearing: Clearing,
    warriors_to_move: int,
    clearing_to_move_tunnel_from: Clearing | None = None,
):
    """Dig action: place or move a tunnel and move warriors.

    Args:
        player: The Moles player
        card: The card being used
        clearing: The clearing to dig in
        warriors_to_move: Number of warriors to move from burrow to clearing
        clearing_to_move_tunnel_from: If provided, tunnel is moved from here
                                       If None, tunnel is placed from supply

    Raises:
        IllegalActionError if card not in hand, clearing already has tunnel, etc.
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.ACTIONS)

    # Validate card is in hand
    card_entry = validate_card_in_hand(player, card)

    # Capture card before discarding (for logging)
    card_model = card_entry.card

    # Validate clearing for digging (no tunnel present, card valid for clearing)
    validate_dig_clearing(player, clearing, card)

    # Validate max 4 warriors can be moved
    if warriors_to_move > 4:
        raise IllegalActionError("Can move a maximum of 4 warriors in one dig action")

    # Get burrow and validate warriors available
    burrow = Burrow.objects.get(player=player)
    warriors_in_burrow = Warrior.objects.filter(player=player, clearing=burrow).count()
    if warriors_in_burrow < warriors_to_move:
        raise IllegalActionError(
            f"Not enough warriors in burrow. Have {warriors_in_burrow}, need {warriors_to_move}"
        )

    # Handle tunnel placement/movement
    if clearing_to_move_tunnel_from is None:
        # Place tunnel from supply
        tunnel = Tunnel.objects.filter(player=player, clearing__isnull=True).first()
        if tunnel is None:
            raise IllegalActionError("No tunnels left in supply")
        place_piece_from_supply_into_clearing(tunnel, clearing)
    else:
        # Move tunnel from source clearing
        validate_tunnel_source_clearing(player, clearing_to_move_tunnel_from)
        tunnel = Tunnel.objects.get(
            player=player, clearing=clearing_to_move_tunnel_from
        )
        # remove tunnel from source and replace it at new clearing
        tunnel.clearing = None
        tunnel.save()
        place_piece_from_supply_into_clearing(tunnel, clearing)

    # Move warriors from burrow to clearing
    move_warriors(player, burrow, clearing, warriors_to_move)

    # Discard card
    discard_card_from_hand(player, card_entry)

    # Log the action
    tunnel_from_cn = (
        clearing_to_move_tunnel_from.clearing_number
        if clearing_to_move_tunnel_from
        else None
    )
    phase_log = get_current_phase_log(player.game, player)
    log_moles_dig(
        player.game,
        player,
        clearing.clearing_number,
        CardSerializer(card_model).data,
        warriors_to_move,
        tunnel_from_cn,
        parent=phase_log,
    )

    # Decrement actions
    decrement_actions(player)
