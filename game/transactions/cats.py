from django.db import transaction
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.cats.buildings import CatBuildingTypes, Sawmill, Workshop
from game.models.cats.tokens import CatWood
from game.models.cats.turn import CatBirdsong, CatDaylight, CatTurn
from game.models.game_models import Clearing, HandEntry, Piece, Player, Suit
from game.queries.cats.building import (
    get_score_after_placement,
    get_usable_wood_for_building,
    get_wood_cost,
)
from game.queries.cats.crafting import validate_crafting_pieces_satisfy_requirements
from game.queries.cats.turn import get_phase
from game.queries.cats.wood import get_sawmills_by_suit
from game.queries.general import (
    available_building_slot,
    validate_player_has_card_in_hand,
)
from game.transactions.general import craft_card, discard_card_from_hand, raise_score
from game.utility.textchoice import next_choice
from django.apps import apps


@transaction.atomic
def produce_wood(player: Player, sawmill: Sawmill):
    """not to be used for overwork. use for birdsong"""
    # check that sawmill is not used
    if sawmill.building_slot is None:
        raise ValueError("Sawmill is not placed")
    if sawmill.used:
        raise ValueError("Sawmill is already used")
    # check that sawmill is player's
    if sawmill.player != player:
        raise ValueError("Sawmill is not owned by player")
    # get a supply wood token to place
    wood_token = CatWood.objects.filter(player=player, clearing=None).first()
    if wood_token is None:
        raise ValueError("No wood tokens left to place")
    # assign wood token to sawmill clearing

    wood_token.clearing = sawmill.building_slot.clearing
    wood_token.save()
    sawmill.used = True
    sawmill.save()
    # check if all sawmills have been used
    print(
        Sawmill.objects.filter(player=player, used=False, building_slot__isnull=False)
    )
    if not Sawmill.objects.filter(
        player=player, used=False, building_slot__isnull=False
    ).exists():
        print("all sawmills used")
        # move to next part of phase
        phase = get_phase(player)
        if type(phase) == CatBirdsong:
            phase.step = next_choice(CatBirdsong.CatBirdsongSteps, phase.step)
            print(phase.step)
            phase.save()

        else:
            raise ValueError(
                f"Wrong phase type, should be CatBirdsong, got {type(phase)}"
            )


@transaction.atomic
def create_cats_turn(player: Player):
    # create turn
    turn = CatTurn.create_turn(player)


@transaction.atomic
def build_building(
    player: Player,
    building_type: CatBuildingTypes,
    clearing: Clearing,
    wood_tokens: list[CatWood],
):
    """builds a building of the given type in the given clearing using the given wood tokens"""
    # verify that all objects belong to the same game
    game = player.game
    if clearing.game != game:
        raise ValueError("All objects must belong to the same game")
    for token in wood_tokens:
        if token.player != player:
            raise ValueError("All tokens must belong to the same player")
    # check that there aren't duplicate tokens
    if len(wood_tokens) != len(set(wood_tokens)):
        raise ValueError("Duplicate tokens provided")
    # check that provided wood tokens are enough to build building
    required_wood = get_wood_cost(player, building_type)
    if required_wood is None:
        raise ValueError("No building of that type in supply")
    if len(wood_tokens) < required_wood:
        raise ValueError("Not enough wood tokens provided to build this building")

    # verify that selected wood tokens are part of the valid set (connected wood)
    available_wood = get_usable_wood_for_building(player, building_type, clearing)
    if available_wood is None:
        raise ValueError("Not enough connected wood to build")
    available_wood = set(available_wood)
    if not all([token in available_wood for token in wood_tokens]):
        raise ValueError("provided wood tokens are not all connected to the clearing")
    # increase points
    scoring = get_score_after_placement(player, building_type)
    if scoring is None:
        raise ValueError("Building type not in supply. how did we get this far?")
    raise_score(player, scoring)
    # place the building
    building_slot = available_building_slot(clearing)
    if building_slot is None:
        raise ValueError("No free building slots")
    building_model = apps.get_model("game", building_type.value)
    building = building_model.objects.filter(player=player, building_slot=None).first()
    building.building_slot = building_slot
    building.save()
    # remove wood tokens from board
    for token in wood_tokens:
        token.clearing = None
        token.save()


@transaction.atomic
def action_used(player: Player):
    """reduces the actions remaining during cats daylight stage by 1"""
    daylight = get_phase(player)
    if type(daylight) != CatDaylight:
        raise ValueError("Not Daylight phase")
    if daylight.actions_left == 0:
        raise ValueError("No actions remaining")
    daylight.actions_left -= 1
    daylight.save()


@transaction.atomic
def overwork(player: Player, clearing: Clearing, card: CardsEP):
    """overworks a sawmill in the given clearing, discarding the card from the player's hand"""
    # check that player has card in hand
    hand_entry = validate_player_has_card_in_hand(player, card)
    # check that player has a sawmill in given clearing, and that the suit matches the card
    sawmills = get_sawmills_by_suit(player, card.value.suit.convert_to_textchoice())
    if not sawmills.filter(clearing=clearing).exists():
        raise ValueError("No sawmill in that clearing")
    # check that there is wood left to produce
    wood_token = CatWood.objects.filter(clearing=None, player=player).first()
    if wood_token is None:
        raise ValueError("No wood tokens left to overwork")
    # place wood token at clearing
    wood_token.clearing = clearing
    wood_token.save()
    # remove card from player's hand
    discard_card_from_hand(player, hand_entry)
    # reduce actions remaining
    action_used(player)


@transaction.atomic
def birds_for_hire(player: Player, card: CardsEP):
    """uses the given card to gain an action"""
    # check that player has card in hand/get card instance
    hand_entry = validate_player_has_card_in_hand(player, card)
    # check that card is a bird card
    if card.value.suit != Suit.WILD:
        print(card.value.suit)
        raise ValueError("Not a bird card")
    # check that there is a daylight phase
    daylight = get_phase(player)
    if type(daylight) != CatDaylight:
        raise ValueError("Not Daylight phase")
    # gain action
    daylight.actions_left += 1
    daylight.save()
    # remove card from player's hand
    discard_card_from_hand(player, hand_entry)


@transaction.atomic
def cat_craft_card(player: Player, card: CardsEP, crafting_pieces: list[Workshop]):

    card_in_hand = validate_player_has_card_in_hand(player, card)
    if not validate_crafting_pieces_satisfy_requirements(player, card, crafting_pieces):
        raise ValueError("Not enough crafting pieces to craft card")
    craft_card(card_in_hand, crafting_pieces)
