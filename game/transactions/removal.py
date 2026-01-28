from game.models import CatKeep
from game.models.events.battle import Battle
from game.models.game_models import (
    Building,
    Clearing,
    Faction,
    Game,
    Player,
    Token,
    Warrior,
    CoffinWarrior,
)
from game.transactions.cats import create_field_hospital_event
from game.transactions.outrage import create_outrage_event
from game.queries.crafted_cards import get_coffin_makers_player


def return_warrior_to_supply(warrior: Warrior):
    """Returns a warrior to the supply, or to Coffin Makers if it exists."""
    game = warrior.player.game
    coffin_player = get_coffin_makers_player(game)

    if coffin_player:
        CoffinWarrior.warrior_to_coffin(warrior)
    else:
        warrior.clearing = None
        warrior.save()


def battler_removes_all_pieces(game: Game, battle: Battle, defender: bool):
    """removes all pieces of defender (if True) or attacker (if False) from the battle clearing"""
    removing_player = Player.objects.get(
        game=game, faction=battle.attacker if defender else battle.defender
    )
    removed_player = Player.objects.get(
        game=game, faction=battle.defender if defender else battle.attacker
    )
    warrior_count = Warrior.objects.filter(
        clearing=battle.clearing, player=removed_player
    ).count()
    player_removes_warriors(
        battle.clearing, removing_player, removed_player, warrior_count
    )
    tokens = Token.objects.filter(clearing=battle.clearing, player=removed_player)
    for token in tokens:
        player_removes_token(game, token, removing_player)
    buildings = Building.objects.filter(
        building_slot__clearing=battle.clearing, player=removed_player
    )
    for building in buildings:
        player_removes_building(game, building, removing_player)


def player_removes_warriors(
    clearing: Clearing, removing_player: Player, removed_player: Player, count: int
):
    """removes warriors from the board by player, triggering any relevant events"""
    if count == 0:
        return
    warriors = list(Warrior.objects.filter(clearing=clearing, player=removed_player)[:count])
    if len(warriors) != count:
        raise ValueError("Not enough warriors to remove")

    # For Cats, we launch Field Hospital event if keep is not destroyed. 
    # Warriors are temporarily moved to clearing=None (supply) so they can be saved to keep.
    # If not saved, they will eventually go to Coffin/Supply via return_warrior_to_supply.

    if removed_player.faction == Faction.CATS and not CatKeep.objects.get(player=removed_player).destroyed:
        for warrior in warriors:
            warrior.clearing = None
            warrior.save()
        create_field_hospital_event(clearing, removed_player, count)
    else:
        # Non-cat warriors go through the coffin check immediately
        for warrior in warriors:
            return_warrior_to_supply(warrior)


def player_removes_token(game: Game, token: Token, removing_player: Player):
    """removes a token from the board by player, scoring points and triggering any relevant events"""
    clearing = token.clearing
    # check faction relevant events
    # check if token is a sympathy token
    wa_player = Player.objects.get(game=game, faction=Faction.WOODLAND_ALLIANCE)
    if token in Token.objects.filter(player=wa_player, clearing=clearing):
        # launch Outrage event
        wa_player = Player.objects.get(game=game, faction=Faction.WOODLAND_ALLIANCE)
        create_outrage_event(token.clearing, removing_player, wa_player)
    #if token is the keep, mark as destroyed
    cat_player = Player.objects.get(game=game, faction=Faction.CATS)
    keep = CatKeep.objects.get(player=cat_player)
    if token.pk == keep.pk:
        keep.destroyed = True
        keep.save()

    
    # remove token
    token.clearing = None
    token.save()
    # remover scores a point
    removing_player.score += 1
    removing_player.save()

def player_removes_building(game: Game, building: Building, removing_player: Player):
    """removes a building from the board by player, scoring points and triggering any relevant events"""
    building.building_slot = None
    building.save()
    # remover scores a point
    removing_player.score += 1
    removing_player.save()
    # check faction relevant events
