from game.models import DiscardPileEntry
from game.queries.general import get_enemy_factions_in_clearing
from game.transactions.battle import start_battle
from game.transactions.general import move_warriors
from game.models import Clearing
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.events import EyrieEmigreEvent
from game.models import CraftedCardEntry
from django.db import transaction
from game.models.game_models import Faction, Player

@transaction.atomic
def is_emigre(player: Player) -> bool:
    """ checks if the player has an unused eyrie emigre card
    if so, returns True and launches event
    """
    eyrie_emigre = CraftedCardEntry.objects.filter(player=player, card__card_type=CardsEP.EYRIE_EMIGRE.name, used=CraftedCardEntry.UsedChoice.UNUSED).first()
    has_eyrie_emigre = eyrie_emigre is not None
    if has_eyrie_emigre:
        EyrieEmigreEvent.create(crafted_card_entry=eyrie_emigre)
    return has_eyrie_emigre

@transaction.atomic
def emigre_move(event: EyrieEmigreEvent, origin: Clearing, destination: Clearing, count: int):
    """
    execute the move action for eyrie emigre event
    Mark the move as completed on the event, and mark the destination clearing
    """
    player = event.crafted_card_entry.player
    # check move hasn't been done yet
    if event.move_completed:
        raise ValueError("Move already completed")
    move_warriors(player, origin, destination, count)
    event.move_completed = True
    event.move_destination = destination
    event.save()
    # if no enemy in destination, trigger emigre_failure
    enemy_factions = get_enemy_factions_in_clearing(destination)
    if len(enemy_factions) == 0:
        emigre_failure(event)

@transaction.atomic
def emigre_battle(event: EyrieEmigreEvent, target_faction : Faction):
    """
    Initiate battle in destination_clearing of emigre event against target_faction
    Mark the battle as initiated on the event,
    mark the card as used, and resolve the event
    """
    if event.battle_initiated:
        raise ValueError("Battle already initiated")
    if not event.move_completed:
        raise ValueError("Move must be completed before battle")
    game = event.event.game
    clearing = event.move_destination
    assert clearing is not None, "Destination Clearing of Emigre Event is None!"
    attacking_faction = event.crafted_card_entry.player.faction
    defending_faction = target_faction
    start_battle(game, clearing, attacking_faction, defending_faction)
    #mark battle initiated
    event.battle_initiated = True
    event.save()
    #mark card as used
    event.crafted_card_entry.used = CraftedCardEntry.UsedChoice.USED
    event.crafted_card_entry.save()
    #mark event as resolved
    event.event.resolved = True
    event.event.save()


@transaction.atomic
def emigre_failure(event: EyrieEmigreEvent):
    """
    Execute the failure action for eyrie emigre event
    resolve the event, and discard the crafted card
    """
    #mark event as resolved
    event.event.resolved = True
    event.event.save()
    #discard the crafted card
    card = event.crafted_card_entry.card
    event.crafted_card_entry.delete()
    #event is now deleted due to cascade
    DiscardPileEntry.create_from_card(card)

