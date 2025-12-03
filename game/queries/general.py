from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models import (
    Building,
    BuildingSlot,
    Clearing,
    CraftedCardEntry,
    Faction,
    Player,
    Token,
    Warrior,
)
from game.models.game_models import Game


def available_building_slot(clearing: Clearing) -> BuildingSlot | None:
    building_slots = BuildingSlot.objects.filter(clearing=clearing)
    for building_slot in building_slots:
        if not Building.objects.filter(building_slot=building_slot).exists():
            return building_slot
    return None


def determine_clearing_rule(clearing: Clearing) -> Player | None:
    """returns the player who controls the clearing or None if no player controls it"""
    rule_score_dict = {}
    pieces_in_clearing = []
    # tally up warriors in clearing
    pieces_in_clearing.extend(list(Warrior.objects.filter(clearing=clearing)))
    # tally up buldings in clearing
    pieces_in_clearing.extend(
        list(Building.objects.filter(building_slot__clearing=clearing))
    )
    # need to tally up soup kitchens if relevant
    ## TODO: add soup kitchen card logic
    ## search crafted cards for soup kitchen
    ## if found, tally up tokens of that player
    soupy_players = list(
        CraftedCardEntry.objects.filter(
            player__game=clearing.game, card__card_type=CardsEP.SOUP_KITCHENS.name
        )
    )
    for player in soupy_players:
        # look up tokens in clearing of that player
        tokens = list(Token.objects.filter(clearing=clearing, player=player.player))
        pieces_in_clearing.extend(tokens * 2)

    for piece in pieces_in_clearing:
        if piece.player not in rule_score_dict:
            rule_score_dict[piece.player] = 1
        else:
            rule_score_dict[piece.player] += 1
    max_score = 0
    players_with_max_score = []
    for player, score in rule_score_dict.items():
        if score > max_score:
            max_score = score
            players_with_max_score = [player]
        elif score == max_score:
            players_with_max_score.append(player)
    if len(players_with_max_score) == 1:
        return players_with_max_score[0]
    else:  # if birds among tied, they rule
        for player in players_with_max_score:
            if player.faction == Faction.BIRDS:
                return player
        return None


def player_has_warriors_in_clearing(player: Player, clearing: Clearing) -> bool:
    """returns True if player has warriors in clearing"""
    return Warrior.objects.filter(clearing=clearing, player=player).exists()


def get_current_player(game: Game) -> Player:
    return Player.objects.get(game=game, turn_order=game.current_turn)
