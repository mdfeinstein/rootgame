from django.db import transaction

from game.models import Clearing, Player, Warrior
from game.models.game_models import Faction
from game.models.moles.setup import MolesSimpleSetup
from game.models.moles.buildings import Citadel, Market
from game.models.moles.tokens import Tunnel
from game.models.moles.crown import Crown
from game.models.moles.ministers import Minister
from game.models.moles.burrow import Burrow
from game.models.events.setup import GameSimpleSetup
from game.errors import UnavailableActionError, IllegalActionError
from game.queries.setup.moles import validate_corner
from game.transactions.setup_util import next_player_setup
from game.transactions.general import place_warriors_into_clearing
from game.utility.textchoice import next_choice


@transaction.atomic
def create_moles_warrior_supply(player: Player):
    """create 20 moles warriors"""
    warriors = [Warrior(player=player) for _ in range(20)]
    for warrior in warriors:
        warrior.save()


@transaction.atomic
def create_moles_buildings(player: Player):
    """create 3 citadels and 3 markets (in supply, null clearing)"""
    for i in range(3):
        Citadel(player=player, building_slot=None).save()
        Market(player=player, building_slot=None).save()


@transaction.atomic
def create_moles_tunnels(player: Player):
    """create 3 tunnels (in supply, null clearing)"""
    for i in range(3):
        Tunnel(player=player, clearing=None).save()


@transaction.atomic
def create_moles_crowns(player: Player):
    """create 9 crowns: three of each type (SQUIRE, NOBLE, LORD)"""
    for _ in range(3):
        Crown.objects.create(player=player, type=Crown.CrownType.SQUIRE, used=False)
        Crown.objects.create(player=player, type=Crown.CrownType.NOBLE, used=False)
        Crown.objects.create(player=player, type=Crown.CrownType.LORD, used=False)


@transaction.atomic
def create_moles_ministers(player: Player):
    """create all 9 ministers, unswayed and unused"""
    ministers = [
        Minister(
            player=player, name=Minister.MinisterName.MARSHAL, swayed=False, used=False
        ),
        Minister(
            player=player, name=Minister.MinisterName.CAPTAIN, swayed=False, used=False
        ),
        Minister(
            player=player, name=Minister.MinisterName.FOREMOLE, swayed=False, used=False
        ),
        Minister(
            player=player,
            name=Minister.MinisterName.BRIGADIER,
            swayed=False,
            used=False,
        ),
        Minister(
            player=player, name=Minister.MinisterName.MAYOR, swayed=False, used=False
        ),
        Minister(
            player=player, name=Minister.MinisterName.BANKER, swayed=False, used=False
        ),
        Minister(
            player=player,
            name=Minister.MinisterName.DUCHESS_OF_MUD,
            swayed=False,
            used=False,
        ),
        Minister(
            player=player,
            name=Minister.MinisterName.EARL_OF_STONE,
            swayed=False,
            used=False,
        ),
        Minister(
            player=player,
            name=Minister.MinisterName.BARON_OF_DIRT,
            swayed=False,
            used=False,
        ),
    ]
    for minister in ministers:
        minister.save()


@transaction.atomic
def create_moles_burrow(player: Player):
    """create a single burrow for the moles player"""
    # The Burrow is a special clearing that only this player can access
    burrow = Burrow(
        game=player.game,
        player=player,
        suit=None,  # Burrow doesn't have a suit
    )
    burrow.save()


@transaction.atomic
def start_simple_moles_setup(player: Player) -> MolesSimpleSetup:
    """initialize all moles pieces for setup"""
    create_moles_warrior_supply(player)
    create_moles_buildings(player)
    create_moles_tunnels(player)
    create_moles_crowns(player)
    create_moles_ministers(player)
    create_moles_burrow(player)
    setup = MolesSimpleSetup(player=player, step=MolesSimpleSetup.Steps.PICKING_CORNER)
    setup.save()
    return setup


@transaction.atomic
def pick_corner(player: Player, clearing: Clearing):
    """place burrow in a corner clearing and distribute initial warriors and tunnel"""
    # check that it is moles setup
    simple_setup = GameSimpleSetup.objects.get(game=player.game)
    if simple_setup.status != GameSimpleSetup.GameSetupStatus.MOLES_SETUP:
        raise UnavailableActionError("Not this player's setup turn")

    moles_setup = MolesSimpleSetup.objects.get(player=player)
    if moles_setup.step != MolesSimpleSetup.Steps.PICKING_CORNER:
        raise UnavailableActionError("this has been triggered at the wrong step")

    # validate corner clearing
    validate_corner(player.game, clearing)

    # place 2 warriors and 1 tunnel in the corner clearing
    place_warriors_into_clearing(player, clearing, 2)

    tunnel_in_corner = Tunnel.objects.filter(
        player=player, clearing__isnull=True
    ).first()
    assert tunnel_in_corner is not None, "no tunnel in supply during moles setup!"
    tunnel_in_corner.clearing = clearing
    tunnel_in_corner.save()

    # place 2 warriors in each adjacent clearing
    adjacent_clearings = clearing.connected_clearings.all()
    for adjacent_clearing in adjacent_clearings:
        place_warriors_into_clearing(player, adjacent_clearing, 2)

    # update setup
    moles_setup.step = next_choice(MolesSimpleSetup.Steps, moles_setup.step)
    moles_setup.save()

    from game.serializers.logs.moles import log_moles_setup_pick_corner

    log_moles_setup_pick_corner(player.game, player, clearing.clearing_number)


@transaction.atomic
def confirm_completed_setup(player: Player):
    """confirm moles setup is complete and move to next player"""
    moles_setup = MolesSimpleSetup.objects.get(player=player)
    if moles_setup.step != MolesSimpleSetup.Steps.PENDING_CONFIRMATION:
        raise UnavailableActionError("this has been triggered at the wrong step")
    moles_setup.step = next_choice(MolesSimpleSetup.Steps, moles_setup.step)
    moles_setup.save()
    # move to next step in general setup (next player, perhaps)
    next_player_setup(player.game)
