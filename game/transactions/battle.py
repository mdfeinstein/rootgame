from game.game_data.general.game_enums import Suit
from game.queries.general import validate_player_has_card_in_hand
from random import randint
from django.db import transaction

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.birds.player import BirdLeader
from game.models.events.battle import Battle
from game.models.events.event import Event, EventType
from game.models.game_models import (
    Building,
    Card,
    Clearing,
    Faction,
    Game,
    HandEntry,
    Piece,
    Player,
    Token,
    Warrior,
)
from game.models.wa.tokens import WASympathy
from game.queries.general import (
    count_player_pieces_in_clearing,
    player_has_pieces_in_clearing,
    player_has_warriors_in_clearing,
    warrior_count_in_clearing,
)
from game.transactions.general import discard_card_from_hand
from game.transactions.removal import (
    player_removes_building,
    player_removes_token,
    player_removes_warriors,
)


@transaction.atomic
def start_battle(game: Game, attacker: Faction, defender: Faction, clearing: Clearing):
    """starts a battle between the given factions at the given clearing"""
    # check that attacker and defender are not the same faction
    if attacker == defender:
        raise ValueError("Attacker and defender cannot be the same faction")
    # check that attacker has warriors in the clearing
    player = Player.objects.get(game=game, faction=attacker)

    if not player_has_warriors_in_clearing(player, clearing):
        raise ValueError("Attacker does not have warriors in that clearing")
    # check that defender has pieces in the clearing
    if not player_has_pieces_in_clearing(player, clearing):
        raise ValueError("Defender does not have pieces in that clearing")
    # create battle
    event = Event.objects.create(game=game, type=EventType.BATTLE)
    battle = Battle(
        attacker=attacker, defender=defender, clearing=clearing, event=event
    )
    battle.save()


@transaction.atomic
def defender_ambush_choice(game: Game, battle: Battle, ambush_card: CardsEP | None):
    """
    if ambush_card is None, defender chooses not to ambush
    else, defender uses this card to ambush.
    """
    # check the timing
    if battle.step != Battle.BattleSteps.DEFENDER_AMBUSH_CHECK:
        raise ValueError("Not defender ambush check step")
    # if ambush_card is None, defender chooses not to ambush
    if ambush_card is None:
        battle.defender_ambush = False
        battle.step = Battle.BattleSteps.ROLL_DICE
        battle.save()
        roll_dice(game, battle)
        return
    else:
        defender_player = Player.objects.get(game=game, faction=battle.defender)
        #check that card is in hand
        card_in_hand = validate_player_has_card_in_hand(defender_player, ambush_card)
        # check that card is actually an ambush
        if ambush_card.value.ambush is False:
            raise ValueError("Card is not an ambush")
        # check that suit matches clearing
        if card_in_hand.card.suit != battle.clearing.suit and card_in_hand.card.suit != Suit.WILD:
            raise ValueError("Card suit does not match clearing suit") 
        # flag the battle as ambushed
        battle.defender_ambush = True
        battle.step = Battle.BattleSteps.ATTACKER_AMBUSH_CANCEL_CHECK
        battle.save()
        # spend card
        discard_card_from_hand(defender_player, card_in_hand)


@transaction.atomic
def attacker_ambush_choice(game: Game, battle: Battle, ambush_card: CardsEP | None):
    """
    if ambush_card is None, attacker chooses not to cancel ambush
    else, attacker uses this card to cancel ambush.
    """
    # check the timing
    if battle.step != Battle.BattleSteps.ATTACKER_AMBUSH_CANCEL_CHECK:
        raise ValueError("Not attacker ambush cancel check step")
    # if no ambush card, attacker chooses not to cancel ambush
    defending_player = Player.objects.get(game=game, faction=battle.defender)
    attacking_player = Player.objects.get(game=game, faction=battle.attacker)
    if ambush_card is None:
        battle.attacker_cancel_ambush = False
        attacking_player = Player.objects.get(game=game, faction=battle.attacker)
        attacking_warriors = warrior_count_in_clearing(
            attacking_player, battle.clearing
        )
        if attacking_warriors > 2:
            # resolve ambush by removing attacking warriors and proceeding to roll
            player_removes_warriors(
                battle.clearing, attacking_player, defending_player, 2
            )
            battle.step = Battle.BattleSteps.ROLL_DICE
            battle.save()
            roll_dice(game, battle)
            return
        elif attacking_warriors == 2:
            # resolve ambush by removing attacking warriors and ending the battle
            player_removes_warriors(
                battle.clearing, defending_player, attacking_player, 2
            )
            end_battle(game, battle)
            return
        else:
            # resolve ambush by removing remaining attacking warrior and moving to attacker choosing their hits
            player_removes_warriors(
                battle.clearing, attacking_player, defending_player, 1
            )
            # do i need to convey that attacker must choose one hit, or is this kind of guaranteed to only be one?
            battle.step = Battle.BattleSteps.ATTACKER_CHOOSE_AMBUSH_HITS
            battle.save()
            return
    # if ambush, check that card is actually an ambush and get the hand entry
    if ambush_card.value.ambush is False:
        raise ValueError("Card is not an ambush")
    if ambush_card.value.suit != battle.clearing.suit and ambush_card.value.suit != Suit.WILD:
        raise ValueError("Card suit does not match clearing suit")
    attacker_player = Player.objects.get(game=game, faction=battle.attacker)    
    card_in_hand = validate_player_has_card_in_hand(attacker_player, ambush_card)
    # spend card
    discard_card_from_hand(attacker_player, card_in_hand)
    # flag the battle as ambushed
    battle.attacker_cancel_ambush = True
    battle.step = Battle.BattleSteps.ROLL_DICE
    battle.save()
    # roll dice
    roll_dice(game, battle)


def roll_dice(game: Game, battle: Battle):
    """rolls the dice for the battle"""
    # check the timing
    if battle.step != Battle.BattleSteps.ROLL_DICE:
        raise ValueError("Not roll dice step")
    die1 = randint(0, 3)
    die2 = randint(0, 3)
    print(f"dice rolled: {die1}, {die2}")
    hi, lo = max(die1, die2), min(die1, die2)
    attacking_player = Player.objects.get(game=game, faction=battle.attacker)
    defending_player = Player.objects.get(game=game, faction=battle.defender)
    attacking_warriors_count = warrior_count_in_clearing(
        attacking_player, battle.clearing
    )
    defending_warriors_count = warrior_count_in_clearing(
        defending_player, battle.clearing
    )
    # assign hits, accounting for woodland alliance guerilla warfare
    if battle.defender != Faction.WOODLAND_ALLIANCE:
        # limit hits by warrior count
        hi = min(hi, attacking_warriors_count)
        lo = min(lo, defending_warriors_count)
        # assign hits
        battle.defender_hits_taken += hi
        battle.attacker_hits_taken += lo
    else:
        # limit hits by warrior count
        hi = min(hi, defending_warriors_count)
        lo = min(lo, attacking_warriors_count)
        # assign hits
        battle.attacker_hits_taken += hi
        battle.defender_hits_taken += lo
    # assign other additional hits and reducers...
    # undefended extra hit
    if defending_warriors_count == 0:
        battle.defender_hits_taken += 1
    # birds commander extra hit
    if battle.attacker == Faction.BIRDS:
        birds_player = Player.objects.get(game=game, faction=Faction.BIRDS)
        print(f'bird leaders: {[(leader.leader, leader.active) for leader in BirdLeader.objects.filter(player=birds_player)]}')
        if (
            BirdLeader.objects.get(player=birds_player, active=True).leader
            == BirdLeader.BirdLeaders.COMMANDER
        ):
            battle.attacker_hits_taken += 1
    # assign hits automatically if possible. otherwise, go to choice steps
    if defending_warriors_count >= battle.defender_hits_taken:
        player_removes_warriors(
            battle.clearing,
            attacking_player,
            defending_player,
            battle.defender_hits_taken,
        )
        battle.defender_hits_assigned = battle.defender_hits_taken
    else:
        # remove warriors and tally assigned hits, and then move on to choice stage if anything else left to hit and more hits to assign
        battle.defender_hits_assigned = defending_warriors_count
        player_removes_warriors(
            battle.clearing,
            attacking_player,
            defending_player,
            defending_warriors_count,
        )
        pieces_left_to_hit = count_player_pieces_in_clearing(
            defending_player, battle.clearing
        )
        defender_hits_left_to_assign = (
            battle.defender_hits_taken - battle.defender_hits_assigned
        )
        if defender_hits_left_to_assign > 0 and pieces_left_to_hit > 0:
            if pieces_left_to_hit <= defender_hits_left_to_assign:
                tokens = Token.objects.filter(
                    clearing=battle.clearing, player=defending_player
                )
                for token in tokens:
                    player_removes_token(game, token, attacking_player)
                buildings = Building.objects.filter(
                    building_slot__clearing=battle.clearing, player=defending_player
                )
                for building in buildings:
                    player_removes_building(game, building, attacking_player)

            else:  # more pieces than hits, go to choice step
                battle.step = Battle.BattleSteps.DEFENDER_CHOOSE_HITS
                battle.save()

    if attacking_warriors_count >= battle.attacker_hits_taken:
        player_removes_warriors(
            battle.clearing,
            defending_player,
            attacking_player,
            battle.attacker_hits_taken,
        )
        battle.attacker_hits_assigned = battle.attacker_hits_taken
    else:
        # remove warriors and tally assigned hits, and then move on to choice stage if any more hits to assign, and pieces left to hit
        battle.attacker_hits_assigned = attacking_warriors_count
        player_removes_warriors(
            battle.clearing,
            defending_player,
            attacking_player,
            attacking_warriors_count,
        )
        attacking_pieces_count = count_player_pieces_in_clearing(
            attacking_player, battle.clearing
        )
        attacking_hits_left_to_assign = (
            battle.attacker_hits_taken - battle.attacker_hits_assigned
        )
        if attacking_hits_left_to_assign > 0 and attacking_pieces_count > 0:
            if attacking_pieces_count <= attacking_hits_left_to_assign:
                # remove all pieces, don't need to do choice step
                tokens = Token.objects.filter(
                    clearing=battle.clearing, player=attacking_player
                )
                for token in tokens:
                    player_removes_token(game, token, defending_player)
                buildings = Building.objects.filter(
                    building_slot__clearing=battle.clearing, player=attacking_player
                )
                for building in buildings:
                    player_removes_building(game, building, defending_player)
            else:  # more pieces than hits, go to choice step if not already on defender choice step
                if battle.step != Battle.BattleSteps.DEFENDER_CHOOSE_HITS:
                    battle.step = Battle.BattleSteps.ATTACKER_CHOOSE_HITS

    if battle.step == Battle.BattleSteps.ROLL_DICE:
        # if we havent moved to choice steps, then all needed hits have been assigned and we can move on.
        end_battle(game, battle)
    battle.save()


def defender_chooses_hit(game: Game, battle: Battle, piece: Piece):
    pass


def end_battle(game: Game, battle: Battle):
    """ends the battle and updates the battle and event objects"""
    # update battle
    battle.step = Battle.BattleSteps.COMPLETED
    battle.save()
    # update event
    event = battle.event
    event.is_resolved = True
    event.save()
