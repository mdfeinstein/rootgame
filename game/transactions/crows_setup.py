from game.models.game_models import Faction, Suit
from game.models.crows.turn import CrowTurn
from django.db import transaction
from game.models.crows.setup import CrowsSimpleSetup
from game.models.crows.tokens import PlotToken
from game.models.events.setup import GameSimpleSetup
from game.models import (
    Clearing,
    Game,
    Player,
    Warrior,
)
from game.transactions.general import place_piece_from_supply_into_clearing
from game.transactions.setup_util import next_player_setup
from game.utility.textchoice import next_choice

@transaction.atomic
def create_crows_warrior_supply(player: Player):
    assert player.faction == Faction.CROWS
    for _ in range(15):
        Warrior(player=player).save()

@transaction.atomic
def create_crows_plot_supply(player: Player):
    # create 8 plots (2 of each)
    for plot_type in PlotToken.PlotType:
        PlotToken(player=player, plot_type=plot_type, is_facedown=True).save()
        PlotToken(player=player, plot_type=plot_type, is_facedown=True).save()


@transaction.atomic
def start_simple_crows_setup(player: Player) -> CrowsSimpleSetup:
    create_crows_warrior_supply(player)
    create_crows_plot_supply(player)
    setup = CrowsSimpleSetup(player=player, step=CrowsSimpleSetup.Steps.WARRIOR_PLACE)
    setup.save()
    return setup


@transaction.atomic
def place_initial_warrior(player: Player, clearing: Clearing):
    if player.faction != Faction.CROWS:
        raise ValueError("Player is not Corvid Conspiracy")
    if clearing.game != player.game:
        raise ValueError("Clearing is not in the same game as the player")
    
    setup = CrowsSimpleSetup.objects.get(player=player)
    if setup.step != CrowsSimpleSetup.Steps.WARRIOR_PLACE:
        raise ValueError("Not in warrior placement step")
        
    suit = Suit(clearing.suit)
    if suit == Suit.RED and setup.fox_placed:
        raise ValueError("Fox clearing warrior already placed")
    elif suit == Suit.YELLOW and setup.rabbit_placed:
        raise ValueError("Rabbit clearing warrior already placed")
    elif suit == Suit.ORANGE and setup.mouse_placed:
        raise ValueError("Mouse clearing warrior already placed")
    elif suit == Suit.WILD:
        # Based on user feedback: "there are no wild clearings" unless special maps,
        # but the Autumn map doesn't use them. Standard root doesn't have bird clearings setup
        raise ValueError("Cannot place on a bird clearing during setup")

    from game.models.cats.tokens import CatKeep
    try:
        keep = CatKeep.objects.get(player__game=player.game)
        if keep.clearing == clearing:
            raise ValueError("Cannot place in the keep clearing")
    except CatKeep.DoesNotExist:
        pass

    # Place the warrior
    warrior = Warrior.objects.filter(player=player, clearing__isnull=True).first()
    if warrior is None:
        raise ValueError("No warriors left to place! But this is setup so that's impossible")
        
    place_piece_from_supply_into_clearing(warrior, clearing)

    # Mark suit as placed
    if suit == Suit.RED:
        setup.fox_placed = True
    elif suit == Suit.YELLOW:
        setup.rabbit_placed = True
    elif suit == Suit.ORANGE:
        setup.mouse_placed = True
        
    if setup.fox_placed and setup.rabbit_placed and setup.mouse_placed:
        setup.step = next_choice(CrowsSimpleSetup.Steps, setup.step)
        
    setup.save()

@transaction.atomic
def confirm_completed_setup(player: Player):
    simple_setup = GameSimpleSetup.objects.get(game=player.game)
    # The setup turn logic will hit the correct player based on game_setup order
    
    setup = CrowsSimpleSetup.objects.get(player=player)
    if setup.step != CrowsSimpleSetup.Steps.PENDING_CONFIRMATION:
        raise ValueError("Setup not complete")
        
    setup.step = next_choice(CrowsSimpleSetup.Steps, setup.step)
    setup.save()
    
    # create first turn
    turn_counts = CrowTurn.objects.filter(player=player).count()
    crow_turn = CrowTurn.create_turn(player=player)
    
    # go to next player setup
    next_player_setup(player.game)
