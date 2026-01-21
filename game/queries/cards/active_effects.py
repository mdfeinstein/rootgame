from game.models.game_models import CraftedCardEntry, Faction, Player
from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening
from game.models.wa.turn import WABirdsong, WADaylight, WAEvening
from game.models.cats.turn import CatBirdsong, CatDaylight, CatEvening
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.queries.general import get_current_phase, is_start_of_phase, is_phase


def can_use_card(player: Player, card_entry: CraftedCardEntry) -> bool:
    """
    Returns True if the player can use the crafted card active effect now.
    """
    # 1. Check if card is already used
    if card_entry.used == CraftedCardEntry.UsedChoice.USED:
        return False

    card = card_entry.card.enum  # CardsEP enum
    
    # helper for phase checking
    phase = get_current_phase(player)
    
    if phase is None:
        return False

    # 2. Card Specific Checks
    match card:
        case CardsEP.SABOTEURS:
            # "At start of Birdsong"
            if player.faction == Faction.BIRDS:
                 return is_start_of_phase(player, BirdBirdsong)
            elif player.faction == Faction.WOODLAND_ALLIANCE:
                return is_start_of_phase(player, WABirdsong)
            elif player.faction == Faction.CATS:
                return is_start_of_phase(player, CatBirdsong)

        case CardsEP.EYRIE_EMIGRE | CardsEP.FALSE_ORDERS | CardsEP.SWAP_MEET:
            # "At end of Birdsong" or "In Birdsong" or "Once in Birdsong"
            return is_phase(player, "Birdsong")

        case CardsEP.INFORMANTS:
             # "In Evening, if you would draw cards"
             if not is_phase(player, "Evening"):
                 return False
             
             if player.faction == Faction.BIRDS:
                return phase.step == BirdEvening.BirdEveningSteps.DRAWING
             elif player.faction == Faction.WOODLAND_ALLIANCE:
                return phase.step == WAEvening.WAEveningSteps.DRAWING
             elif player.faction == Faction.CATS:
                return phase.step == CatEvening.CatEveningSteps.DRAWING

        case CardsEP.CHARM_OFFENSIVE:
            # "At start of Evening"
            if player.faction == Faction.BIRDS:
                return is_start_of_phase(player, BirdEvening)
            elif player.faction == Faction.WOODLAND_ALLIANCE:
                return is_start_of_phase(player, WAEvening)
            elif player.faction == Faction.CATS:
                return is_start_of_phase(player, CatEvening)

        case CardsEP.LEAGUE_OF_ADVENTURERS | CardsEP.PROPAGANDA_BUREAU:
            # "Once in Daylight"
            return is_phase(player, "Daylight")

    # If no match or conditions not met
    return False

def has_active_effect(card_entry: CraftedCardEntry) -> bool:
    """
    Returns True if the card has an active effect.
    """
    return not card_entry.used == CraftedCardEntry.UsedChoice.NOT_APPLICABLE 

def is_used(card_entry: CraftedCardEntry) -> bool:
    """
    Returns True if the card has been used.
    """
    return card_entry.used == CraftedCardEntry.UsedChoice.USED