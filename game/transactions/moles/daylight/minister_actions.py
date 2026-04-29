from typing import Literal
from django.db import transaction

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.enums import Faction
from game.models.game_models import Player, RevealedCardEntry, Clearing
from game.models.moles.turn import MoleDaylight
from game.models.moles.ministers import Minister
from game.models.moles.buildings import Citadel, Market
from game.models.moles.tokens import Tunnel
from game.errors import IllegalActionError, UnavailableActionError
from game.queries.moles.turn import validate_step, get_phase
from game.queries.moles.daylight import (
    get_available_building_from_supply,
    validate_card_in_hand,
    validate_foremole_clearing,
    validate_banker_cards,
    validate_brigadier_action,
    validate_no_brigadier_in_progress,
    validate_minister_unused,
)
from game.transactions.general import (
    move_warriors,
    discard_card_from_hand,
)
from game.transactions.battle import start_battle
from game.transactions.moles.turn import next_step
from game.transactions.general import raise_score


def check_all_ministers_used(player: Player):
    """Check if all swayed ministers have been used, advance to next step if so."""
    are_unused_ministers = Minister.objects.filter(
        player=player, swayed=True, used=False
    ).exists()
    if not are_unused_ministers:
        next_step(player)


@transaction.atomic
def skip_brigadier(player: Player):
    """Skip the second Brigadier action and mark the effect complete.

    Args:
        player: The Moles player

    Raises:
        IllegalActionError if Brigadier action is not in progress
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)

    phase = get_phase(player)
    if not isinstance(phase, MoleDaylight):
        raise UnavailableActionError("Not in Daylight phase")

    if phase.brigadier_action == MoleDaylight.BrigadierAction.NONE:
        raise IllegalActionError("No Brigadier action in progress to skip")

    # Reset to NONE
    phase.brigadier_action = MoleDaylight.BrigadierAction.NONE
    phase.save()


def execute_marshal_move(
    player: Player, origin: Clearing, target: Clearing, count: int
):
    """Execute Marshal move action.

    Args:
        player: The Moles player
        origin: The clearing to move warriors from
        target: The clearing to move warriors to
        count: The number of warriors to move
    """
    move_warriors(player, origin, target, count)


@transaction.atomic
def use_marshal(player: Player, origin: Clearing, target: Clearing, count: int):
    """Use the Marshal minister to move warriors.

    Args:
        player: The Moles player
        origin: The clearing to move warriors from
        target: The clearing to move warriors to
        count: The number of warriors to move

    Raises:
        IllegalActionError if Marshal already used this turn
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)
    validate_no_brigadier_in_progress(player)

    marshal = validate_minister_unused(player, Minister.MinisterName.MARSHAL)

    # Use the minister
    marshal.used = True
    marshal.save()

    # Execute action
    execute_marshal_move(player, origin, target, count)

    # Check if all swayed ministers are used
    check_all_ministers_used(player)


@transaction.atomic
def execute_captain_battle(player: Player, defender: Faction, clearing: Clearing):
    """Execute Captain battle action.

    Args:
        player: The Moles player
        defender: The defending faction
        clearing: The clearing where battle occurs
    """
    start_battle(
        player.game,
        attacker=Faction(player.faction),
        defender=defender,
        clearing=clearing,
    )


@transaction.atomic
def use_captain(player: Player, defender: Faction, clearing: Clearing):
    """Use the Captain minister to start a battle.

    Args:
        player: The Moles player
        defender: The defending faction
        clearing: The clearing where battle occurs

    Raises:
        IllegalActionError if Captain already used this turn
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)
    validate_no_brigadier_in_progress(player)

    captain = validate_minister_unused(player, Minister.MinisterName.CAPTAIN)

    # Use the minister
    captain.used = True
    captain.save()

    # Execute action
    execute_captain_battle(player, defender, clearing)

    # Check if all swayed ministers are used
    check_all_ministers_used(player)


def execute_foremole_build(
    player: Player,
    card: CardsEP,
    clearing: Clearing,
    building_type: Literal["citadel", "market"],
):
    """Execute Foremole build action.

    Args:
        player: The Moles player
        card: The card being played
        clearing: The clearing to build in
        building_type: "citadel" or "market"
    """
    # Validate card is in hand and get card entry
    card_entry = validate_card_in_hand(player, card)

    # Validate clearing is ruled and has building slot (card doesn't need to match for Foremole)
    building_slot = validate_foremole_clearing(player, clearing)

    # Get building from supply and place it
    building_instance = get_available_building_from_supply(player, building_type)
    building_instance.building_slot = building_slot
    building_instance.save()

    # Reveal card
    RevealedCardEntry.hand_to_revealed(card_entry)


@transaction.atomic
def use_foremole(
    player: Player,
    card: CardsEP,
    clearing: Clearing,
    building_type: Literal["citadel", "market"],
):
    """Use the Foremole minister to place a building.

    Args:
        player: The Moles player
        card: The card being played
        clearing: The clearing to build in
        building_type: "citadel" or "market"

    Raises:
        IllegalActionError if Foremole already used, card not in hand, etc.
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)
    validate_no_brigadier_in_progress(player)

    foremole = validate_minister_unused(player, Minister.MinisterName.FOREMOLE)

    # Use the minister
    foremole.used = True
    foremole.save()

    # Execute action
    execute_foremole_build(player, card, clearing, building_type)

    # Check if all swayed ministers are used
    check_all_ministers_used(player)


def execute_banker_craft(player: Player, cards: list[CardsEP]):
    """Execute Banker craft action.

    Args:
        player: The Moles player
        cards: List of cards, all same suit (Wild matches any suit)
    """
    card_entries = validate_banker_cards(player, cards)
    raise_score(player, len(cards))
    for card_entry in card_entries:
        discard_card_from_hand(player, card_entry)


@transaction.atomic
def use_banker(player: Player, cards: list[CardsEP]):
    """Use the Banker minister to gain points from a card set.

    Args:
        player: The Moles player
        cards: List of cards, all same suit (Wild matches any suit)

    Raises:
        IllegalActionError if not all cards in hand or not same suit
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)
    validate_no_brigadier_in_progress(player)

    banker = validate_minister_unused(player, Minister.MinisterName.BANKER)

    # Use the minister
    banker.used = True
    banker.save()

    # Execute action
    execute_banker_craft(player, cards)

    # Check if all swayed ministers are used
    check_all_ministers_used(player)


@transaction.atomic
def use_duchess(player: Player):
    """Use the Duchess of Mud minister to gain points if all tunnels are on map.

    Args:
        player: The Moles player

    Raises:
        IllegalActionError if Duchess already used
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)
    validate_no_brigadier_in_progress(player)

    duchess = validate_minister_unused(player, Minister.MinisterName.DUCHESS_OF_MUD)

    # Use the minister
    duchess.used = True
    duchess.save()

    # Check if all tunnels are on map
    tunnels_in_supply = Tunnel.objects.filter(
        player=player, clearing__isnull=True
    ).exists()
    if not tunnels_in_supply:
        raise_score(player, 2)

    # Check if all swayed ministers are used
    check_all_ministers_used(player)


@transaction.atomic
def use_baron(player: Player):
    """Use the Baron of Dirt minister to gain points from markets on map.

    Args:
        player: The Moles player

    Raises:
        IllegalActionError if Baron already used
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)
    validate_no_brigadier_in_progress(player)

    baron = validate_minister_unused(player, Minister.MinisterName.BARON_OF_DIRT)

    # Use the minister
    baron.used = True
    baron.save()

    # Count markets on map
    markets_on_map = Market.objects.filter(
        player=player, building_slot__isnull=False
    ).count()
    raise_score(player, markets_on_map)

    # Check if all swayed ministers are used
    check_all_ministers_used(player)


@transaction.atomic
def use_earl(player: Player):
    """Use the Earl of Stone minister to gain points from citadels on map.

    Args:
        player: The Moles player

    Raises:
        IllegalActionError if Earl already used
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)
    validate_no_brigadier_in_progress(player)

    earl = validate_minister_unused(player, Minister.MinisterName.EARL_OF_STONE)

    # Use the minister
    earl.used = True
    earl.save()

    # Count citadels on map
    citadels_on_map = Citadel.objects.filter(
        player=player, building_slot__isnull=False
    ).count()
    raise_score(player, citadels_on_map)

    # Check if all swayed ministers are used
    check_all_ministers_used(player)


def execute_brigadier_battle(player: Player, defender: Faction, clearing: Clearing):
    """Execute Brigadier battle action and manage state transitions.

    Args:
        player: The Moles player
        defender: The defending faction
        clearing: The clearing where battle occurs
    """
    phase = get_phase(player)
    if not isinstance(phase, MoleDaylight):
        raise UnavailableActionError("Not in Daylight phase")

    # Update state
    if phase.brigadier_action == MoleDaylight.BrigadierAction.MOVE:
        raise IllegalActionError(
            "Must use brigadier for move since first brigadier action was move"
        )
    if phase.brigadier_action == MoleDaylight.BrigadierAction.NONE:
        phase.brigadier_action = MoleDaylight.BrigadierAction.BATTLE
    else:  # BATTLE -> NONE (second action)
        phase.brigadier_action = MoleDaylight.BrigadierAction.NONE
    phase.save()

    # Initiate battle
    start_battle(
        player.game,
        attacker=Faction(player.faction),
        defender=defender,
        clearing=clearing,
    )


def execute_brigadier_move(
    player: Player, origin: Clearing, target: Clearing, count: int
):
    """Execute Brigadier move action and manage state transitions.

    Args:
        player: The Moles player
        origin: The clearing to move warriors from
        target: The clearing to move warriors to
        count: The number of warriors to move
    """
    phase = get_phase(player)
    if not isinstance(phase, MoleDaylight):
        raise UnavailableActionError("Not in Daylight phase")

    # Update state
    if phase.brigadier_action == MoleDaylight.BrigadierAction.BATTLE:
        raise IllegalActionError(
            "Must use brigadier for battle since first brigadier action was battle"
        )
    if phase.brigadier_action == MoleDaylight.BrigadierAction.NONE:
        phase.brigadier_action = MoleDaylight.BrigadierAction.MOVE
    else:  # MOVE -> NONE (second action)
        phase.brigadier_action = MoleDaylight.BrigadierAction.NONE
    phase.save()

    # Move warriors
    move_warriors(player, origin, target, count)


@transaction.atomic
def use_brigadier(player: Player, action: Literal["move", "battle"], *args):
    """Use Brigadier to perform an action (move or battle, can do twice).

    Args:
        player: The Moles player
        action: "move" or "battle"
        *args: Arguments to pass to execute function

    Raises:
        IllegalActionError if trying to mix actions or invalid action type
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)
    validate_no_brigadier_in_progress(player)

    phase = get_phase(player)
    if not isinstance(phase, MoleDaylight):
        raise UnavailableActionError("Not in Daylight phase")

    # Validate action type
    action_type = (
        MoleDaylight.BrigadierAction.BATTLE
        if action == "battle"
        else MoleDaylight.BrigadierAction.MOVE
    )
    validate_brigadier_action(phase, action_type)

    # on first action, Validate brigadier unused and mark as used
    if phase.brigadier_action == MoleDaylight.BrigadierAction.NONE:
        brigadier = validate_minister_unused(player, Minister.MinisterName.BRIGADIER)
        brigadier.used = True
        brigadier.save()

    # Delegate to execute function
    if action == "move":
        execute_brigadier_move(player, *args)
    else:  # action == "battle"
        execute_brigadier_battle(player, *args)

    # Check if all swayed ministers are used
    check_all_ministers_used(player)


@transaction.atomic
def use_mayor(player: Player, minister_name: Minister.MinisterName, *args):
    """Use the Mayor minister to copy another swayed minister's action.

    Args:
        player: The Moles player
        minister_name: The MinisterName of the minister to copy
        *args: Arguments to pass to the copied minister's execute function

    Raises:
        IllegalActionError if Mayor already used, minister not swayed, or unknown minister
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)
    validate_no_brigadier_in_progress(player)

    mayor = validate_minister_unused(player, Minister.MinisterName.MAYOR)

    # Validate the copied minister is swayed
    copied_minister = Minister.objects.filter(player=player, name=minister_name).first()
    if copied_minister is None:
        raise IllegalActionError(f"Minister {minister_name} not found")
    if not copied_minister.swayed:
        raise IllegalActionError(f"Minister {minister_name} must be swayed to copy")

    # Mark Mayor as used
    mayor.used = True
    mayor.save()

    # Dispatch to the appropriate execute function
    if minister_name == Minister.MinisterName.MARSHAL:
        execute_marshal_move(player, *args)
    elif minister_name == Minister.MinisterName.CAPTAIN:
        execute_captain_battle(player, *args)
    elif minister_name == Minister.MinisterName.FOREMOLE:
        execute_foremole_build(player, *args)
    elif minister_name == Minister.MinisterName.BRIGADIER:
        # Brigadier needs special handling: first arg is "move" or "battle"
        action = args[0]
        remaining_args = args[1:]
        if action == "move":
            execute_brigadier_move(player, *remaining_args)
        elif action == "battle":
            execute_brigadier_battle(player, *remaining_args)
        else:
            raise IllegalActionError(f"Unknown brigadier action: {action}")
    elif minister_name == Minister.MinisterName.BANKER:
        execute_banker_craft(player, *args)
    else:
        raise IllegalActionError(f"Cannot copy minister {minister_name}")

    # Check if all swayed ministers are used
    check_all_ministers_used(player)
