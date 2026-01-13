from django.db import transaction
from game.models.game_models import (
    Game, DeckEntry, DiscardPileEntry, Card, Item, Ruin, 
    CraftableItemEntry, CraftedItemEntry, Player, Warrior, 
    Building, Token, HandEntry, Faction, Clearing, BuildingSlot
)
from game.models.birds.buildings import BirdRoost
from game.models.birds.player import DecreeEntry, Vizier, BirdLeader
from game.models.cats.buildings import Workshop, Sawmill, Recruiter
from game.models.cats.tokens import CatKeep, CatWood
from game.models.wa.buildings import WABase
from game.models.wa.tokens import WASympathy
from game.models.wa.player import SupporterStackEntry, OfficerEntry

@transaction.atomic
def load_gamestate(game_id: int, gamestate_data: dict):
    game = Game.objects.get(pk=game_id)
    
    # Restore general game state
    game.current_turn = gamestate_data.get('current_turn', game.current_turn)
    game.boardmap = gamestate_data.get('boardmap', game.boardmap)
    game.save()

    # Restore Deck
    DeckEntry.objects.filter(game=game).delete()
    deck_entries = [
        DeckEntry(game=game, card_id=e['card'], spot=e['spot']) 
        for e in gamestate_data.get('deck', [])
    ]
    DeckEntry.objects.bulk_create(deck_entries)
    
    # Restore Discard Pile
    DiscardPileEntry.objects.filter(game=game).delete()
    discard_entries = [
        DiscardPileEntry(game=game, card_id=e['card'], spot=e['spot'])
        for e in gamestate_data.get('discard', [])
    ]
    DiscardPileEntry.objects.bulk_create(discard_entries)
    
    # Restore Items
    all_game_items = {item.item_type: item for item in Item.objects.filter(game=game)}
    # Reset all items to unexhausted state
    for item in all_game_items.values():
        item.exhausted = False
        item.save()

    # Restore Craftable Items
    CraftableItemEntry.objects.filter(game=game).delete()
    craftable_entries = []
    for entry in gamestate_data.get('craftable_items', []):
        itype = entry['item']['item_type']
        item_obj = all_game_items.get(itype)
        if item_obj:
            item_obj.exhausted = entry['item']['exhausted']
            item_obj.save()
            craftable_entries.append(CraftableItemEntry(game=game, item=item_obj))
    CraftableItemEntry.objects.bulk_create(craftable_entries)

    # Restore Crafted Items
    CraftedItemEntry.objects.filter(player__game=game).delete()
    crafted_entries = []
    for entry in gamestate_data.get('crafted_items', []):
         itype = entry['item']['item_type']
         item_obj = all_game_items.get(itype)
         target_player = Player.objects.get(pk=entry['player_id'])
         if item_obj:
             item_obj.exhausted = entry['item']['exhausted']
             item_obj.save()
             crafted_entries.append(CraftedItemEntry(player=target_player, item=item_obj))
    CraftedItemEntry.objects.bulk_create(crafted_entries)

    # Restore Ruins
    for ruin_data in gamestate_data.get('ruins', []):
        item_type = ruin_data['item']['item_type']
        c_num = ruin_data.get('clearing_number')
        s_num = ruin_data.get('building_slot_number')
        
        item_obj = all_game_items.get(item_type)
        if item_obj:
             ruin = Ruin.objects.filter(game=game, item=item_obj).first()
             if ruin:
                 if c_num is not None and s_num is not None:
                     clearing = Clearing.objects.get(game=game, clearing_number=c_num)
                     slot = BuildingSlot.objects.get(clearing=clearing, building_slot_number=s_num)
                     ruin.building_slot = slot
                 else:
                     ruin.building_slot = None
                 ruin.save()

    # Restore Players
    for p_data in gamestate_data.get('players', []):
        player = Player.objects.get(pk=p_data['id'])
        player.score = p_data['score']
        player.turn_order = p_data['turn_order']
        player.save()
        
        # Restore Hand
        HandEntry.objects.filter(player=player).delete()
        hand_entries = [
            HandEntry(player=player, card_id=e['card'])
            for e in p_data.get('hand', [])
        ]
        HandEntry.objects.bulk_create(hand_entries)

        # Restore Faction Specific State
        load_faction_state(player, p_data.get('faction_state', {}))

def load_faction_state(player, data):
    # Reset common pieces
    Warrior.objects.filter(player=player).update(clearing=None)
    Building.objects.filter(player=player).update(building_slot=None)
    Token.objects.filter(player=player).update(clearing=None)

    # Restore Warriors
    warriors = list(Warrior.objects.filter(player=player))
    w_idx = 0
    for w_data in data.get('warriors', []):
        c_num = w_data.get('clearing_number')
        if c_num is not None:
             clearing = Clearing.objects.get(game=player.game, clearing_number=c_num)
             if w_idx < len(warriors):
                 warriors[w_idx].clearing = clearing
                 warriors[w_idx].save()
                 w_idx += 1

    # Buildings & Tokens
    if player.faction == Faction.BIRDS:
        # Restore Roosts
        roosts = list(BirdRoost.objects.filter(player=player))
        r_idx = 0
        b_data = data.get('buildings', {})
        for r_entry in b_data.get('roosts', []):
            # r_entry structure matches BirdBuildingSerializer
            bs_data = r_entry.get('building', {})
            c_num = bs_data.get('clearing_number')
            s_num = bs_data.get('building_slot_number')
            if c_num is not None and s_num is not None:
                clearing = Clearing.objects.get(game=player.game, clearing_number=c_num)
                slot = BuildingSlot.objects.get(clearing=clearing, building_slot_number=s_num)
                if r_idx < len(roosts):
                    roosts[r_idx].building_slot = slot
                    roosts[r_idx].crafted_with = r_entry.get('crafted_with', False)
                    roosts[r_idx].save()
                    r_idx += 1
        
        # Restore Decree
        DecreeEntry.objects.filter(player=player).delete()
        for d_entry in data.get('decree', []):
            card_data = d_entry.get('card')
            card_id = card_data['id'] if isinstance(card_data, dict) else card_data
            DecreeEntry.objects.create(
                player=player,
                column=d_entry['column'],
                card_id=card_id,
                fulfilled=d_entry['fulfilled']
            )

        # Leaders
        BirdLeader.objects.filter(player=player).update(active=False, available=True)
        for l_entry in data.get('leaders', []):
             leader_obj = BirdLeader.objects.get(player=player, leader=l_entry['leader'])
             leader_obj.active = l_entry['active']
             leader_obj.available = l_entry['available']
             leader_obj.save()

        # Viziers
        Vizier.objects.filter(player=player).delete()
        for v_entry in data.get('viziers', []):
             Vizier.objects.create(player=player, column=v_entry['column'], fulfilled=v_entry['fulfilled'])

    elif player.faction == Faction.CATS:
        # Restore Buildings (Workshops, Recruiters, Sawmills)
        b_data = data.get('buildings', {})
        
        # Helper for restoring cat buildings
        def restore_cat_buildings(model_cls, entry_list, extra_fields=[]):
            objs = list(model_cls.objects.filter(player=player))
            idx = 0
            for entry in entry_list:
                bs_data = entry.get('building', {})
                c_num = bs_data.get('clearing_number')
                s_num = bs_data.get('building_slot_number')
                if c_num is not None and s_num is not None:
                    clearing = Clearing.objects.get(game=player.game, clearing_number=c_num)
                    slot = BuildingSlot.objects.get(clearing=clearing, building_slot_number=s_num)
                    if idx < len(objs):
                        objs[idx].building_slot = slot
                        for field in extra_fields:
                            setattr(objs[idx], field, entry.get(field))
                        objs[idx].save()
                        idx += 1

        restore_cat_buildings(Workshop, b_data.get('workshops', []), ['crafted_with'])
        restore_cat_buildings(Sawmill, b_data.get('sawmills', []), ['used'])
        restore_cat_buildings(Recruiter, b_data.get('recruiters', []), ['used'])

        # Restore Tokens (Keep, Wood)
        t_data = data.get('tokens', {})
        def restore_cat_tokens(model_cls, entry_list, extra_fields=[]):
            objs = list(model_cls.objects.filter(player=player))
            idx = 0
            for entry in entry_list:
                ts_data = entry.get('token', {})
                c_num = ts_data.get('clearing_number')
                if c_num is not None:
                     clearing = Clearing.objects.get(game=player.game, clearing_number=c_num)
                     if idx < len(objs):
                         objs[idx].clearing = clearing
                         for field in extra_fields:
                             setattr(objs[idx], field, entry.get(field))
                         objs[idx].save()
                         idx += 1
        
        restore_cat_tokens(CatKeep, t_data.get('keep', []))
        restore_cat_tokens(CatWood, t_data.get('wood', []))

    elif player.faction == Faction.WOODLAND_ALLIANCE:
        # Restore Bases
        b_data = data.get('buildings', {})
        bases = list(WABase.objects.filter(player=player))
        idx = 0
        for b_entry in b_data.get('base', []):
             bs_data = b_entry.get('building', {})
             c_num = bs_data.get('clearing_number')
             s_num = bs_data.get('building_slot_number')
             if c_num is not None and s_num is not None:
                  clearing = Clearing.objects.get(game=player.game, clearing_number=c_num)
                  slot = BuildingSlot.objects.get(clearing=clearing, building_slot_number=s_num)
                  if idx < len(bases):
                      bases[idx].building_slot = slot
                      bases[idx].suit = b_entry.get('suit')
                      bases[idx].save()
                      idx += 1
        
        # Restore Sympathy Tokens
        t_data = data.get('tokens', {})
        symp = list(WASympathy.objects.filter(player=player))
        idx = 0
        for s_entry in t_data.get('sympathy', []):
             ts_data = s_entry.get('token', {})
             c_num = ts_data.get('clearing_number')
             if c_num is not None:
                 clearing = Clearing.objects.get(game=player.game, clearing_number=c_num)
                 if idx < len(symp):
                     symp[idx].clearing = clearing
                     symp[idx].crafted_with = s_entry.get('crafted_with', False)
                     symp[idx].save()
                     idx += 1
        
        # Restore Supporters
        SupporterStackEntry.objects.filter(player=player).delete()
        for sup in data.get('supporters', []):
            SupporterStackEntry.objects.create(player=player, card_id=sup['card'])
            
        # Restore Officers
        OfficerEntry.objects.filter(player=player).delete()
        # Find unused warriors to assign as officers (warriors with no clearing)
        unused_warriors = Warrior.objects.filter(player=player, clearing=None)
        uw_idx = 0
        for off in data.get('officers', []):
             if uw_idx < len(unused_warriors):
                 OfficerEntry.objects.create(
                     player=player, 
                     warrior=unused_warriors[uw_idx], 
                     used=off['used']
                 )
                 uw_idx += 1
