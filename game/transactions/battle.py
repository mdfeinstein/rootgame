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
        # check that card is actually an ambush
        if ambush_card.value.ambush is False:
            raise ValueError("Card is not an ambush")
        # flag the battle as ambushed
        battle.defender_ambush = True
        battle.step = Battle.BattleSteps.ATTACKER_AMBUSH_CANCEL_CHECK
        battle.save()
        # spend card
        card = Card.objects.get(game=game, card_type=ambush_card.name)
        hand_entry = HandEntry.objects.get(player=battle.defender, card=card)
        discard_card_from_hand(battle.defender, hand_entry)


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
    if ambush_card is None:
        battle.attacker_cancel_ambush = False
        attacking_player = Player.objects.get(game=game, faction=battle.attacker)
        attacking_warriors = warrior_count_in_clearing(
            attacking_player, battle.clearing
        )
        if attacking_warriors > 2:
            # resolve ambush by removing attacking warriors and proceeding to roll
            Warrior.objects.filter(clearing=battle.clearing, player=attacking_player)[
                :2
            ].update(clearing=None)
            battle.step = Battle.BattleSteps.ROLL_DICE
            battle.save()
            roll_dice(game, battle)
            return
        elif attacking_warriors == 2:
            # resolve ambush by removing attacking warriors and ending the battle
            Warrior.objects.filter(clearing=battle.clearing, player=attacking_player)[
                :2
            ].update(clearing=None)
            end_battle(game, battle)
            return
        else:
            # resolve ambush by removing remaining attacking warrior and moving to attacker choosing their hits
            Warrior.objects.filter(
                clearing=battle.clearing, player=attacking_player
            ).update(clearing=None)
            # do i need to convey that attacker must choose one hit, or is this kind of guaranteed to only be one?
            battle.step = Battle.BattleSteps.ATTACKER_CHOOSE_AMBUSH_HITS
            battle.save()
            return
    # if ambush, check that card is actually an ambush and get the hand entry
    if ambush_card.value.ambush is False:
        raise ValueError("Card is not an ambush")
    card = Card.objects.get(game=game, card_type=ambush_card.name)
    hand_entry = HandEntry.objects.get(player=battle.attacker, card=card)
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
        if (
            BirdLeader.objects.get(player=birds_player, active=True).leader
            == BirdLeader.BirdLeaders.COMMANDER
        ):
            battle.attacker_hits_taken += 1
    # assign hits automatically if possible. otherwise, go to choice steps
    if defending_warriors_count >= battle.defender_hits_taken:
        warriors_to_remove = Warrior.objects.filter(
            clearing=battle.clearing, player=defending_player
        )[: battle.defender_hits_taken]
        for warrior in warriors_to_remove:
            warrior.clearing = None
            warrior.save()
        battle.defender_hits_assigned = battle.defender_hits_taken
    else:
        # remove warriors and tally assigned hits, and then move on to choice stage if anything else left to hit and more hits to assign
        battle.defender_hits_assigned = defending_warriors_count
        Warrior.objects.filter(
            clearing=battle.clearing, player=defending_player
        ).update(clearing=None)
        pieces_left_to_hit = count_player_pieces_in_clearing(
            defending_player, battle.clearing
        )
        defender_hits_left_to_assign = (
            battle.defender_hits_taken - battle.defender_hits_assigned
        )
        if defender_hits_left_to_assign > 0 and pieces_left_to_hit > 0:
            if pieces_left_to_hit <= defender_hits_left_to_assign:
                # remove all pieces, don't need to do choice step
                # this function will remove the pieces and score the points, as well as trigger any relevant events
                # battler_removes_all_pieces(game, battle, defender=True)
                pass
            else:  # more pieces than hits, go to choice step
                battle.step = Battle.BattleSteps.DEFENDER_CHOOSE_HITS
                battle.save()

    if attacking_warriors_count >= battle.attacker_hits_taken:
        warriors_to_remove = Warrior.objects.filter(
            clearing=battle.clearing, player=attacking_player
        )[: battle.attacker_hits_taken]
        for warrior in warriors_to_remove:
            warrior.clearing = None
            warrior.save()
        battle.attacker_hits_assigned = battle.attacker_hits_taken
    else:
        # remove warriors and tally assigned hits, and then move on to choice stage if any more hits to assign, and pieces left to hit
        battle.attacker_hits_assigned = attacking_warriors_count
        Warrior.objects.filter(
            clearing=battle.clearing, player=attacking_player
        ).update(clearing=None)
        attacking_pieces_count = count_player_pieces_in_clearing(
            attacking_player, battle.clearing
        )
        attacking_hits_left_to_assign = (
            battle.attacker_hits_taken - battle.attacker_hits_assigned
        )
        if attacking_hits_left_to_assign > 0 and attacking_pieces_count > 0:
            if attacking_pieces_count <= attacking_hits_left_to_assign:
                # remove all pieces, don't need to do choice step
                # this function will remove the pieces and score the points, as well as trigger any relevant events
                # battler_removes_all_pieces(game, battle, defender = False)
                pass
            else:  # more pieces than hits, go to choice step if not already on defender choice step
                if battle.step != Battle.BattleSteps.DEFENDER_CHOOSE_HITS:
                    battle.step = Battle.BattleSteps.ATTACKER_CHOOSE_HITS

    if battle.step == Battle.BattleSteps.ROLL_DICE:
        # if we havent moved to choice steps, then all needed hits have been assigned and we can move on.
        end_battle(game, battle)
    battle.save()


def defender_chooses_hit(game: Game, battle: Battle, piece: Piece):
    pass


def battler_removes_all_pieces(game: Game, battle: Battle, defender: bool):
    """removes all pieces of defender (if True) or attacker (if False) from the battle clearing"""
    removing_player = Player.objects.get(
        game=game, faction=battle.attacker if defender else battle.defender
    )
    removed_player = Player.objects.get(
        game=game, faction=battle.defender if defender else battle.attacker
    )
    Warrior.objects.filter(clearing=battle.clearing, player=removed_player).update(
        clearing=None
    )
    tokens = Token.objects.filter(clearing=battle.clearing, player=battle.defender)
    for token in tokens:
        player_removes_token(game, token, removing_player)
    buildings = Building.objects.filter(
        building_slot__clearing=battle.clearing, player=battle.defender
    )
    for building in buildings:
        player_removes_building(game, building, removing_player)


def player_removes_token(game: Game, token: Token, removing_player: Player):
    """removes a token from the board by player, scoring points and triggering any relevant events"""
    token.clearing = None
    token.save()
    # remover scores a point
    removing_player.score += 1
    # check faction relevant events

    # check if token is a sympathy token
    if token in [
        WASympathy.objects.filter(player=token.player, clearing=token.clearing)
    ]:
        # launch Outrage event
        pass


def player_removes_building(game: Game, building: Building, removing_player: Player):
    """removes a building from the board by player, scoring points and triggering any relevant events"""
    building.building_slot = None
    building.save()
    # remover scores a point
    removing_player.score += 1
    # check faction relevant events


def end_battle(game: Game, battle: Battle):
    """ends the battle and updates the battle and event objects"""
    # update battle
    battle.step = Battle.BattleSteps.COMPLETED
    battle.save()
    # update event
    event = Event.objects.get(game=game, type=EventType.BATTLE, is_resolved=False)
    event.is_resolved = True
    event.save()
