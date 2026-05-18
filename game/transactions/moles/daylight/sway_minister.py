from django.db import transaction

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Player, RevealedCardEntry
from game.models.enums import Faction
from game.models.moles.turn import MoleDaylight
from game.models.moles.ministers import Minister
from game.errors import IllegalActionError, UnavailableActionError
from game.queries.moles.turn import validate_step
from game.transactions.general import raise_score
from game.transactions.moles.turn import next_step
from game.serializers.general_serializers import CardSerializer
from game.serializers.logs.general import get_current_phase_log
from game.serializers.logs.moles import log_moles_sway_minister


@transaction.atomic
def end_sway_minister(player: Player):
    """End the Sway Minister step and advance to the next step.

    Validates that it's the correct phase/step and the player is Moles.
    """
    validate_step(player, MoleDaylight.MoleDaylightSteps.SWAY_MINISTER)
    if player.faction != Faction.MOLES:
        raise UnavailableActionError("Not a Moles player")
    next_step(player)


@transaction.atomic
def sway_minister(
    player: Player, minister_name: Minister.MinisterName, cards: list[CardsEP]
):
    """Sway a minister using cards.

    Args:
        player: The Moles player
        minister_name: The MinisterName of the minister to sway
        cards: List of cards to use for swaying

    Raises:
        IllegalActionError if minister already swayed, not enough cards, no crown, etc.
    """
    from game.queries.moles.daylight import validate_cards_can_sway_minister
    from game.models.moles.crown import Crown

    validate_step(player, MoleDaylight.MoleDaylightSteps.SWAY_MINISTER)

    # Validate cards can sway the minister (validates minister unswayed, crown available, card count, cards in hand, clearing matching)
    hand_entries = validate_cards_can_sway_minister(player, minister_name, cards)

    # Get minister after validation
    minister = Minister.objects.get(player=player, name=minister_name)

    # Mark minister as swayed
    minister.swayed = True
    minister.save()

    # Mark crown as used
    crown = Crown.objects.filter(player=player, type=minister.crown_type, used=False).first()
    if crown is None:
        raise IllegalActionError(f"No crown of type {minister.crown_type} available")
    crown.used = True
    crown.save()

    # Raise score based on tier
    tier_scores = {
        Crown.CrownType.SQUIRE: 1,
        Crown.CrownType.NOBLE: 2,
        Crown.CrownType.LORD: 3,
    }
    crown_type = Crown.CrownType(minister.crown_type)
    score = tier_scores[crown_type]
    raise_score(player, score)

    # Capture card objects before revealing
    card_objects = [e.card for e in hand_entries]

    # Reveal cards
    for hand_entry in hand_entries:
        RevealedCardEntry.hand_to_revealed(hand_entry)

    # Log the action
    phase_log = get_current_phase_log(player.game, player)
    log_moles_sway_minister(
        player.game,
        player,
        minister_name.value,
        minister.crown_type,
        score,
        CardSerializer(card_objects, many=True).data,
        parent=phase_log,
    )

    # move to next step
    next_step(player)
