from typing import Literal
from typing import Set
from game.models import Ruin
from game.models.game_models import Suit
from game.models import BirdEvening
from game.models.wa.turn import WAEvening
from game.models import CatEvening
from game.models import BirdDaylight
from game.models.wa.turn import WADaylight
from game.models import CatDaylight
from game.models import BirdBirdsong
from game.models.wa.turn import WABirdsong
from game.models.cats.turn import CatBirdsong
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
    WASympathy,
)
from game.models.cats.buildings import Workshop
from game.models.birds.buildings import BirdRoost
from game.models.dominance import DominanceSupplyEntry, ActiveDominanceEntry
from game.models.game_models import Card, Game, HandEntry, Piece


def available_building_slot(clearing: Clearing) -> BuildingSlot | None:
    building_slots = BuildingSlot.objects.filter(clearing=clearing)
    for building_slot in building_slots:
        if (
            not Building.objects.filter(building_slot=building_slot).exists()
            and not Ruin.objects.filter(building_slot=building_slot).exists()
        ):
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


def get_enemy_factions_in_clearing(player: Player, clearing: Clearing) -> list[Faction]:
    """returns a list of opposing factions that have pieces in the clearing"""
    factions = []
    for player_ in Player.objects.filter(game=player.game):
        if player_ != player:
            if player_has_pieces_in_clearing(player_, clearing):
                factions.append(Faction(player_.faction))
    return factions


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


def get_current_phase(player: Player):
    """
    Returns the current active phase model instance for the player.
    Supports Birds, WA, Cats.
    Returns None if no phase is active or faction not supported.
    """
    if player.faction == Faction.BIRDS:
        from game.queries.birds.turn import get_phase as get_bird_phase

        return get_bird_phase(player)
    elif player.faction == Faction.WOODLAND_ALLIANCE:
        from game.queries.wa.turn import get_phase as get_wa_phase

        return get_wa_phase(player)
    elif player.faction == Faction.CATS:
        from game.queries.cats.turn import get_phase as get_cat_phase

        return get_cat_phase(player)

    return None


def is_phase(
    player: Player,
    phase: Literal["Birdsong", "Daylight", "Evening"] | None,
) -> bool:
    """
    Returns True if the player is in the specified phase.
    """
    phase_obj = get_current_phase(player)
    match phase:
        case "Birdsong":
            return isinstance(phase_obj, (CatBirdsong, WABirdsong, BirdBirdsong))
        case "Daylight":
            return isinstance(phase_obj, (CatDaylight, WADaylight, BirdDaylight))
        case "Evening":
            return isinstance(phase_obj, (CatEvening, WAEvening, BirdEvening))
        case _:
            raise ValueError(
                "Invalid phase argument provided. Must be 'Birdsong', 'Daylight', or 'Evening'"
            )


def is_start_of_phase(player: Player, phase_model_class) -> bool:
    """
    Returns True if the player is in the specified phase AND at the first step.
    phase_model_class: The class of the phase to check (e.g. BirdBirdsong)
    """
    phase = get_current_phase(player)
    if not isinstance(phase, phase_model_class):
        return False
    current_step = phase.step
    if current_step == "1":
        return True
    return False


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


def validate_game_has_dominance_card_in_supply(game: Game, card: CardsEP):
    """
    returns DominanceSupplyEntry instance if card is in the dominance supply, else raises ValueError
    """
    from game.models.dominance import DominanceSupplyEntry

    dominance_entry = DominanceSupplyEntry.objects.filter(
        game=game, card__card_type=card.name
    ).first()
    if dominance_entry is None:
        raise ValueError(f"Dominance card not in supply. card name: {card.name}")
    return dominance_entry


def validate_can_activate_dominance(player: Player):
    """validates that player can activate dominance"""
    if player.score < 10:
        raise ValueError("Must have 10 points to activate dominance.")
    if ActiveDominanceEntry.objects.filter(player=player).exists():
        raise ValueError("Already have an active dominance card.")


def validate_player_has_crafted_card(player: Player, card: CardsEP) -> CraftedCardEntry:
    """returns CraftedCardEntry instance if player has card in hand, else raises ValueError
    should only be possible to have one at a time of a specific card
    """
    crafted_card = CraftedCardEntry.objects.filter(
        player=player, card__card_type=card.name
    ).first()
    if crafted_card is None:
        raise ValueError(f"Player does not have card in hand. card name: {card.name}")
    return crafted_card


def card_matches_clearing(card: CardsEP, clearing: Clearing) -> bool:
    """returns True if card suit matches clearing suit"""
    return card.value.suit == Suit(clearing.suit) or card.value.suit == Suit.WILD


def get_player_hand_size(player: Player) -> int:
    """returns the number of cards in the player's hand"""
    return HandEntry.objects.filter(player=player).count()


def get_adjacent_clearings(player: Player, clearing: Clearing) -> set[Clearing]:
    """
    Returns a set of clearings adjacent to the given clearing for the player,
    accounting for passive effects like Boat Builders and Tunnels.
    """
    adjacent = set(clearing.connected_clearings.all())

    # Boat Builders: treat rivers as paths
    if CraftedCardEntry.objects.filter(
        player=player, card__card_type=CardsEP.BOAT_BUILDERS.name
    ).exists():
        adjacent.update(clearing.water_connected_clearings.all())

    # Tunnels: treat clearings with any of your crafting pieces as adjacent
    if CraftedCardEntry.objects.filter(
        player=player, card__card_type=CardsEP.TUNNELS.name
    ).exists():
        # Check if current clearing has any of our crafting pieces
        has_crafting_piece_here = (
            Workshop.objects.filter(
                player=player, building_slot__clearing=clearing
            ).exists()
            or BirdRoost.objects.filter(
                player=player, building_slot__clearing=clearing
            ).exists()
            or WASympathy.objects.filter(player=player, clearing=clearing).exists()
        )
        if has_crafting_piece_here:
            # All other clearings with our crafting pieces are adjacent
            crafting_clearing_ids = set()
            crafting_clearing_ids.update(
                Workshop.objects.filter(
                    player=player, building_slot__isnull=False
                ).values_list("building_slot__clearing_id", flat=True)
            )
            crafting_clearing_ids.update(
                BirdRoost.objects.filter(
                    player=player, building_slot__isnull=False
                ).values_list("building_slot__clearing_id", flat=True)
            )
            crafting_clearing_ids.update(
                WASympathy.objects.filter(
                    player=player, clearing__isnull=False
                ).values_list("clearing_id", flat=True)
            )

            adjacent.update(Clearing.objects.filter(id__in=crafting_clearing_ids))

            # Remove self if it was added
            adjacent.discard(clearing)

    return adjacent


def validate_legal_move(
    player: Player,
    clearing_start: Clearing,
    clearing_end: Clearing,
    ignore_rule: bool = False,
):
    """checks if legal move from clearing_start to clearing_end
    might fail because:
    -- no warriors in origin clearing
    -- clearing_start is not adjacent to clearing_end
    -- player does not control either origin or target clearing
    """
    if not Warrior.objects.filter(clearing=clearing_start, player=player).exists():
        raise ValueError("No warriors in origin clearing")

    # check clearing adjacency (Boat Builders, Tunnels handled here)
    adjacent_clearings = get_adjacent_clearings(player, clearing_start)
    if clearing_end not in adjacent_clearings:
        raise ValueError("clearing_start is not adjacent to clearing_end")

    # Corvid Planners: ignore rule while moving
    try:
        validate_player_has_crafted_card(player, CardsEP.CORVID_PLANNERS)
        has_corvid_planners = True
    except ValueError:
        has_corvid_planners = False
    if has_corvid_planners or ignore_rule:
        return  # skip rulership check
    rule_target = determine_clearing_rule(clearing_end)
    rule_origin = determine_clearing_rule(clearing_start)
    if rule_target != player and rule_origin != player:
        raise ValueError("player does not control either origin or target clearing")


def validate_has_legal_moves(player: Player, clearing: Clearing):
    """raises if no legal moves from the given clearing"""
    # get adjacent clearings
    adjacent_clearings = get_adjacent_clearings(player, clearing)
    for adjacent_clearing in adjacent_clearings:
        try:
            validate_legal_move(player, clearing, adjacent_clearing)
            return True
        except ValueError:
            continue
    raise ValueError("No legal moves from the given clearing")


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
