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
from game.models.game_models import Card, Game, HandEntry, Piece


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


def warrior_count_in_clearing(player: Player, clearing: Clearing) -> int:
    """returns the number of warriors in clearing belonging to player"""
    return Warrior.objects.filter(clearing=clearing, player=player).count()


def warrior_count_in_supply(player: Player) -> int:
    """returns the number of warriors in the player's supply"""
    return Warrior.objects.filter(player=player, clearing=None).count()


def player_has_pieces_in_clearing(player: Player, clearing: Clearing) -> bool:
    """returns True if player has any pieces in clearing"""
    return any(
        [
            Warrior.objects.filter(clearing=clearing, player=player).exists(),
            Building.objects.filter(
                building_slot__clearing=clearing, player=player
            ).exists(),
            Token.objects.filter(clearing=clearing, player=player).exists(),
        ]
    )


def count_player_pieces_in_clearing(player: Player, clearing: Clearing) -> int:
    """returns the number of pieces in clearing belonging to player"""
    return sum(
        [
            Warrior.objects.filter(clearing=clearing, player=player).count(),
            Building.objects.filter(
                building_slot__clearing=clearing, player=player
            ).count(),
            Token.objects.filter(clearing=clearing, player=player).count(),
        ]
    )


def get_current_player(game: Game) -> Player:
    """returns the player whose turn it is"""
    return Player.objects.get(game=game, turn_order=game.current_turn)


def get_crafting_pieces(player: Player, card: CardsEP) -> list[Piece]:
    """returns a list of crafting pieces for the given card"""
    pass


def validate_player_has_card_in_hand(player: Player, card: CardsEP) -> HandEntry:
    """
    returns HandEntry instance if player has card in hand, else raises ValueError
    If multiple cards of the same name are in the player's hand, returns the first one
    """
    card_in_hand = HandEntry.objects.filter(
        player=player, card__card_type=card.name
    ).first()
    if card_in_hand is None:
        raise ValueError(f"Player does not have card in hand. card name: {card.name}")
    return card_in_hand


def get_player_hand_size(player: Player) -> int:
    """returns the number of cards in the player's hand"""
    return HandEntry.objects.filter(player=player).count()


def validate_legal_move(
    player: Player, clearing_start: Clearing, clearing_end: Clearing
):
    """checks if legal move from clearing_start to clearing_end
    might fail because:
    -- no warriors in origin clearing
    -- clearing_start is not adjacent to clearing_end
    -- player does not control either origin or target clearing
    """
    if not Warrior.objects.filter(clearing=clearing_start, player=player).exists():
        raise ValueError("No warriors in origin clearing")
    # check clearing adjacency
    if not clearing_start.connected_clearings.filter(pk=clearing_end.pk).exists():
        raise ValueError("clearing_start is not adjacent to clearing_end")
    # check rule of clearings
    rule_target_or_origin = determine_clearing_rule(
        clearing_end
    ) or determine_clearing_rule(clearing_start)
    if not rule_target_or_origin:
        raise ValueError("player does not control either origin or target clearing")


def validate_has_legal_moves(player: Player, clearing: Clearing):
    """raises if no legal moves from the given clearing"""
    # get adjacent clearings
    adjacent_clearings = clearing.connected_clearings.all()
    for adjacent_clearing in adjacent_clearings:
        validate_legal_move(player, clearing, adjacent_clearing)


def validate_enemy_pieces_in_clearing(
    player: Player, clearing: Clearing
) -> list[Player]:
    """raises if no enemy pieces in the given clearing"""
    # confirm clearing and player are in the same game
    players_with_pieces = []
    if player.game != clearing.game:
        raise ValueError("Player and clearing are not in the same game")
    # get opposing players
    players_in_game = Player.objects.filter(game=player.game)
    for player_ in players_in_game:
        if player_ != player:
            # check if there are any pieces in the clearing
            if player_has_pieces_in_clearing(player_, clearing):
                players_with_pieces.append(player_)
    if len(players_with_pieces) == 0:
        raise ValueError("No enemy pieces in clearing")
    return players_with_pieces
