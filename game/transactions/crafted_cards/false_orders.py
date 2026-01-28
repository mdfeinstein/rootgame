from django.db import transaction
from game.models.game_models import (
    Player,
    Clearing,
    CraftedCardEntry,
    Faction,
    Warrior,
    DiscardPileEntry,
)
from game.queries.general import is_phase, get_current_player
from game.transactions.general import move_warriors

@transaction.atomic
def use_false_orders(
    crafted_card_entry: CraftedCardEntry,
    target_player: Player,
    origin_clearing: Clearing,
    destination_clearing: Clearing,
):
    """
    In Birdsong, may discard this card to move half of enemy's warriors (rounded up)
    from any clearing, as if you were that player, ignoring rule.
    """
    player = crafted_card_entry.player
    # 1. check that target_player is different than crafted_card_entry user
    if player == target_player:
        raise ValueError("Cannot target yourself with False Orders")

    # 2. check that it is the using player's birdsong phase and it is their turn
    if get_current_player(player.game) != player:
        raise ValueError("It is not your turn")
    if not is_phase(player, "Birdsong"):
        raise ValueError("False Orders can only be used during Birdsong")

    # 3. calculate half of target players warriors in origin_clearing (rounding up)
    warrior_count = Warrior.objects.filter(clearing=origin_clearing, player=target_player).count()
    if warrior_count == 0:
        raise ValueError("No enemy warriors in origin clearing")
    
    number_to_move = (warrior_count + 1) // 2

    # 4. call move_warriors(target_player, origin_clearing, destination_clearing, calculated_number, ignore_rule=True)
    move_warriors(
        target_player,
        origin_clearing,
        destination_clearing,
        number_to_move,
        ignore_rule=True,
    )

    # 5. discard the false orders
    card = crafted_card_entry.card
    crafted_card_entry.delete()
    DiscardPileEntry.create_from_card(card)
