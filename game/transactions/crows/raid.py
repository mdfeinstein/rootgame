from django.db import transaction
from game.models.game_models import Player, Clearing, Warrior, Faction
from game.models.crows.tokens import PlotToken
from game.models.events.event import Event, EventType
from game.models.events.crows import CrowRaidEvent
from game.transactions.general import place_piece_from_supply_into_clearing
from game.queries.general import get_adjacent_clearings

@transaction.atomic
def trigger_raid_effect(player: Player, clearing: Clearing, **kwargs):
    """
    Triggers the Raid effect when a Raid token is removed.
    Places one Crow warrior in every adjacent clearing if able.
    If not enough warriors in reserve, launches a CrowRaidEvent.
    """
    parent = kwargs.get("parent")
    adjacent_clearings = list(get_adjacent_clearings(player, clearing))
    
    # Filter valid clearings (e.g. not CatKeep, Snare)
    valid_clearings = []
    from game.queries.general import validate_can_place_piece_in_clearing
    for adj in adjacent_clearings:
        try:
            validate_can_place_piece_in_clearing(player, adj)
            valid_clearings.append(adj)
        except ValueError:
            continue
            
    if not valid_clearings:
        return

    warriors_in_supply = Warrior.objects.filter(player=player, clearing__isnull=True).count()
    
    if warriors_in_supply >= len(valid_clearings):
        # Auto-place in all
        for v_clearing in valid_clearings:
            warrior = Warrior.objects.filter(player=player, clearing__isnull=True).first()
            if warrior:
                place_piece_from_supply_into_clearing(warrior, v_clearing)

        from game.serializers.logs.general import get_active_phase_log
        from game.serializers.logs.crows import log_crows_raid
        log_crows_raid(
            player.game, 
            player, 
            clearing.clearing_number, 
            len(valid_clearings),
            parent=parent if parent else get_active_phase_log(player.game)
        )
    else:
        # Launch event
        event = Event.objects.create(
            game=player.game,
            type=EventType.PLACE_RAID_WARRIORS
        )
        raid_event = CrowRaidEvent.objects.create(
            event=event
        )
        raid_event.remaining_clearings.set(valid_clearings)

@transaction.atomic
def place_raid_warrior(player: Player, clearing: Clearing, event: Event):
    """
    Manually places a raid warrior during a CrowRaidEvent.
    """
    if event.is_resolved:
        raise ValueError("Event is already resolved")
    
    raid_event = CrowRaidEvent.objects.get(event=event)
    if clearing not in raid_event.remaining_clearings.all():
        raise ValueError("Clearing is not valid for this raid effect")
        
    warrior = Warrior.objects.filter(player=player, clearing__isnull=True).first()
    if not warrior:
        raise ValueError("No warriors left in reserve")
        
    place_piece_from_supply_into_clearing(warrior, clearing)
    raid_event.remaining_clearings.remove(clearing)
    
    # if no warriors left in reserve or no clearings left, resolve event.
    warriors_left = Warrior.objects.filter(player=player, clearing__isnull=True).count()
    if warriors_left == 0 or raid_event.remaining_clearings.count() == 0:
        event.is_resolved = True
        event.save()
