"""
deck is an array of Cards where the index is the card id.
Cards contain info like uit, name, crafting cost, crafted text, etc.
all the information that may be needed.
DB only stores the card_id and code will need to com here to look up relevant details
"""

from dataclasses import dataclass
from enum import Enum

from game.game_data.general.game_enums import ItemTypes, Suit


@dataclass
class Card:
    suit: Suit
    title: str
    craftable: bool
    cost: list[Suit]
    text: str = ""
    item: ItemTypes | None = None
    crafted_points: int = 0
    ambush: bool = False
    dominance: bool = False


class CardsEP(Enum):
    SABOTEURS = Card(
        suit=Suit.WILD,
        title="Saboteurs",
        craftable=True,
        cost=[Suit.WILD],
        text="At start of Birdsong, may discard this card to discard an enemy's crafted card.",
    )
    SOUP_KITCHENS = Card(
        suit=Suit.WILD,
        title="Soup Kitchen",
        craftable=True,
        cost=[Suit.RED, Suit.YELLOW, Suit.ORANGE],
        text="Your tokens now count toward rule, and each of your tokens counts twice.",
    )
    BOAT_BUILDERS = Card(
        suit=Suit.WILD,
        title="Boat Builders",
        craftable=True,
        cost=[Suit.WILD, Suit.WILD],
        text="You treat rivers as paths.",
    )
    CORVID_PLANNERS = Card(
        suit=Suit.WILD,
        title="Corvid Planners",
        craftable=True,
        cost=[Suit.WILD, Suit.WILD],
        text="While moving, you ignore rule.",
    )
    EYRIE_EMIGRE = Card(
        suit=Suit.WILD,
        title="Eyrie Emigre",
        craftable=True,
        cost=[Suit.RED, Suit.RED],
        text="At end of Birdsong, take a move, then initiate a battle in the clearing you moved into. If you did not take both actions, discard this card.",
    )
    INFORMANTS = Card(
        suit=Suit.RED,
        title="Informants",
        craftable=True,
        cost=[Suit.RED, Suit.RED],
        text="In Evening, if you would draw cards, you may instead take on ambush card from the discard pile.",
    )
    RABBIT_PARTISANS = Card(
        suit=Suit.YELLOW,
        title="Rabbit Partisans",
        craftable=True,
        cost=[Suit.YELLOW],
        text="In Battle in rabbit clearings, may deal one extra hit, then discard all your cards except rabbits.",
    )
    TUNNELS = Card(
        suit=Suit.YELLOW,
        title="Tunnels",
        craftable=True,
        cost=[Suit.YELLOW],
        text="You treat clearings with any of your crafting pieces as adjacent.",
    )
    CHARM_OFFENSIVE = Card(
        suit=Suit.YELLOW,
        title="Charm Offensive",
        craftable=True,
        cost=[Suit.YELLOW],
        text="At start of Evening, may draw a card and choose another player to score one point.",
    )
    LEAGUE_OF_ADVENTURERS = Card(
        suit=Suit.ORANGE,
        title="League of Adventurous Mice",
        craftable=True,
        cost=[Suit.ORANGE],
        text="Once in Daylight, may exhuast an item in your Crafted Item Box to take a move or initiate a battle.",
    )
    MURINE_BROKERS = Card(
        suit=Suit.ORANGE,
        title="Murine Brokers",
        craftable=True,
        cost=[Suit.ORANGE, Suit.ORANGE],
        text="Whenever another player crafts an item, draw a card.",
    )
    MASTER_ENGRAVERS = Card(
        suit=Suit.ORANGE,
        title="Master Engravers",
        craftable=True,
        cost=[Suit.ORANGE, Suit.ORANGE],
        text="Whenever you craft an item, score one extra point.",
    )
    TRAVEL_GEAR_RED = Card(
        suit=Suit.RED,
        title="Travel Gear",
        craftable=True,
        cost=[Suit.YELLOW],
        crafted_points=1,
        item=ItemTypes.BOOTS,
    )
    PROTECTION_RACKET = Card(
        suit=Suit.RED,
        title="Protection Racket",
        craftable=True,
        cost=[Suit.YELLOW, Suit.YELLOW],
        crafted_points=3,
        item=ItemTypes.COIN,
    )
    FOXFOLK_STEEL = Card(
        suit=Suit.RED,
        title="Foxfolk Steel",
        craftable=True,
        cost=[Suit.RED, Suit.RED],
        crafted_points=2,
        item=ItemTypes.SWORD,
    )
    ANVIL = Card(
        suit=Suit.RED,
        title="Anvil",
        craftable=True,
        cost=[Suit.RED],
        crafted_points=2,
        item=ItemTypes.HAMMER,
    )
    BIRDY_BINDLE = Card(
        suit=Suit.WILD,
        title="Birdy Bindle",
        craftable=True,
        cost=[Suit.ORANGE],
        crafted_points=1,
        item=ItemTypes.BAG,
    )
    TRAVEL_GEAR_ORANGE = Card(
        suit=Suit.ORANGE,
        title="Travel Gear",
        craftable=True,
        cost=[Suit.YELLOW],
        crafted_points=1,
        item=ItemTypes.BOOTS,
    )
    ROOT_TEA_ORANGE = Card(
        suit=Suit.ORANGE,
        title="Root Tea",
        craftable=True,
        cost=[Suit.ORANGE],
        crafted_points=2,
        item=ItemTypes.TEA,
    )
    MOUSE_IN_A_SACK = Card(
        suit=Suit.ORANGE,
        title="Mouse in a Sack",
        craftable=True,
        cost=[Suit.ORANGE],
        crafted_points=1,
        item=ItemTypes.BAG,
    )
    SWORD = Card(
        suit=Suit.ORANGE,
        title="Sword",
        craftable=True,
        cost=[Suit.RED, Suit.RED],
        crafted_points=2,
        item=ItemTypes.SWORD,
    )
    CROSSBOW_ORANGE = Card(
        suit=Suit.ORANGE,
        title="Crossbow",
        craftable=True,
        cost=[Suit.RED],
        crafted_points=1,
        item=ItemTypes.CROSSBOW,
    )
    DOMINANCE_WILD = Card(
        suit=Suit.WILD,
        title="Dominance",
        craftable=False,
        cost=[],
        dominance=True,
    )
    DOMINANCE_RED = Card(
        suit=Suit.RED,
        title="Dominance",
        craftable=False,
        cost=[],
        dominance=True,
    )
    DOMINANCE_YELLOW = Card(
        suit=Suit.YELLOW,
        title="Dominance",
        craftable=False,
        cost=[],
        dominance=True,
    )
    DOMINANCE_ORANGE = Card(
        suit=Suit.ORANGE,
        title="Dominance",
        craftable=False,
        cost=[],
        dominance=True,
    )
    FOX_PARTISANS = Card(
        suit=Suit.RED,
        title="Fox Partisans",
        craftable=True,
        cost=[Suit.RED],
        text="In Battle in fox clearings, may deal one extra hit, then discard all your cards except foxes.",
    )
    PROPAGANDA_BUREAU = Card(
        suit=Suit.RED,
        title="Propaganda Bureau",
        craftable=True,
        cost=[Suit.WILD, Suit.WILD, Suit.WILD],
        text="Once in Daylight, may spend a card to remove an enemy warrior from a matching clearing and place a warrior there.",
    )
    FALSE_ORDERS = Card(
        suit=Suit.RED,
        title="False Orders",
        craftable=True,
        cost=[Suit.RED],
        text="In Birdsong, may discard this card to move half of enemy's warriors (rounded up) from any clearing, as if you were that player, ignoring rule.",
    )
    COFFIN_MAKERS = Card(
        suit=Suit.YELLOW,
        title="Coffin Makers",
        craftable=True,
        cost=[Suit.YELLOW, Suit.YELLOW],
        text="Whenever any warriors would return to a supply, place them on this card instead. At start of Birdsong, you score one point per five warriors here, then return all warriors here to their supplies.",
    )
    SWAP_MEET = Card(
        suit=Suit.YELLOW,
        title="Swap Meet",
        craftable=True,
        cost=[Suit.YELLOW],
        text="Once in Birdsong, may take a random card from another player and then give them a card.",
    )
    MOUSE_PARTISANS = Card(
        suit=Suit.ORANGE,
        title="Mouse Partisans",
        craftable=True,
        cost=[Suit.ORANGE],
        text="In Battle in mouse clearings, may deal one extra hit, then discard all your cards except mice.",
    )
    WOODLAND_RUNNERS = Card(
        suit=Suit.WILD,
        title="Woodland Runners",
        craftable=True,
        cost=[Suit.YELLOW],
        crafted_points=1,
        item=ItemTypes.BOOTS,
    )
    ARMS_TRADER = Card(
        suit=Suit.WILD,
        title="Arms Trader",
        craftable=True,
        cost=[Suit.RED, Suit.RED],
        crafted_points=2,
        item=ItemTypes.SWORD,
    )
    CROSSBOW_WILD = Card(
        suit=Suit.WILD,
        title="Crossbow",
        craftable=True,
        cost=[Suit.RED],
        crafted_points=1,
        item=ItemTypes.CROSSBOW,
    )
    GENTLY_USED_KNAPSACK = Card(
        suit=Suit.RED,
        title="Gently Used Knapsack",
        craftable=True,
        cost=[Suit.ORANGE],
        crafted_points=1,
        item=ItemTypes.BAG,
    )
    ROOT_TEA_RED = Card(
        suit=Suit.RED,
        title="Root Tea",
        craftable=True,
        cost=[Suit.ORANGE],
        crafted_points=2,
        item=ItemTypes.TEA,
    )
    SMUGGLERS_TRAIL = Card(
        suit=Suit.YELLOW,
        title="Smuggler's Trail",
        craftable=True,
        cost=[Suit.ORANGE],
        crafted_points=1,
        item=ItemTypes.BOOTS,
    )
    ROOT_TEA_YELLOW = Card(
        suit=Suit.YELLOW,
        title="Root Tea",
        craftable=True,
        cost=[Suit.ORANGE],
        crafted_points=2,
        item=ItemTypes.TEA,
    )
    A_VISIT_TO_FRIENDS = Card(
        suit=Suit.YELLOW,
        title="A Visit to Friends",
        craftable=True,
        cost=[Suit.YELLOW],
        crafted_points=1,
        item=ItemTypes.BOOTS,
    )
    BAKE_SALE = Card(
        suit=Suit.YELLOW,
        title="Bake Sale",
        craftable=True,
        cost=[Suit.YELLOW, Suit.YELLOW],
        crafted_points=3,
        item=ItemTypes.COIN,
    )
    INVESTMENTS = Card(
        suit=Suit.YELLOW,
        title="Investments",
        craftable=True,
        cost=[Suit.YELLOW, Suit.YELLOW],
        crafted_points=3,
        item=ItemTypes.COIN,
    )
    AMBUSH_RED = Card(
        suit=Suit.RED,
        title="Ambush!",
        craftable=False,
        cost=[],
        ambush=True,
        text="At start of battle, defender may play to deal two immediate hits, then discard. Cancel if attacker plays matching ambush.",
    )
    AMBUSH_YELLOW = Card(
        suit=Suit.YELLOW,
        title="Ambush!",
        craftable=False,
        cost=[],
        ambush=True,
        text="At start of battle, defender may play to deal two immediate hits, then discard. Cancel if attacker plays matching ambush.",
    )
    AMBUSH_ORANGE = Card(
        suit=Suit.ORANGE,
        title="Ambush!",
        craftable=False,
        cost=[],
        ambush=True,
        text="At start of battle, defender may play to deal two immediate hits, then discard. Cancel if attacker plays matching ambush.",
    )
    AMBUSH_WILD = Card(
        suit=Suit.WILD,
        title="Ambush!",
        craftable=False,
        cost=[],
        ambush=True,
        text="At start of battle, defender may play to deal two immediate hits, then discard. Cancel if attacker plays matching ambush.",
    )


deck: list[CardsEP] = [
    CardsEP.SABOTEURS,
    CardsEP.SOUP_KITCHENS,
    CardsEP.BOAT_BUILDERS,
    CardsEP.CORVID_PLANNERS,
    CardsEP.EYRIE_EMIGRE,
    CardsEP.INFORMANTS,
    CardsEP.RABBIT_PARTISANS,
    CardsEP.TUNNELS,
    CardsEP.TUNNELS,
    CardsEP.CHARM_OFFENSIVE,
    CardsEP.LEAGUE_OF_ADVENTURERS,
    CardsEP.MURINE_BROKERS,
    CardsEP.MASTER_ENGRAVERS,
    CardsEP.SABOTEURS,
    CardsEP.SABOTEURS,
    CardsEP.TRAVEL_GEAR_RED,
    CardsEP.PROTECTION_RACKET,
    CardsEP.FOXFOLK_STEEL,
    CardsEP.ANVIL,
    CardsEP.BIRDY_BINDLE,
    CardsEP.TRAVEL_GEAR_ORANGE,
    CardsEP.ROOT_TEA_ORANGE,
    CardsEP.MOUSE_IN_A_SACK,
    CardsEP.SWORD,
    CardsEP.CROSSBOW_ORANGE,
    CardsEP.DOMINANCE_WILD,
    CardsEP.DOMINANCE_RED,
    CardsEP.DOMINANCE_YELLOW,
    CardsEP.DOMINANCE_ORANGE,
    CardsEP.FOX_PARTISANS,
    CardsEP.PROPAGANDA_BUREAU,
    CardsEP.FALSE_ORDERS,
    CardsEP.FALSE_ORDERS,
    CardsEP.INFORMANTS,
    CardsEP.COFFIN_MAKERS,
    CardsEP.SWAP_MEET,
    CardsEP.SWAP_MEET,
    CardsEP.MOUSE_PARTISANS,
    CardsEP.LEAGUE_OF_ADVENTURERS,
    CardsEP.WOODLAND_RUNNERS,
    CardsEP.ARMS_TRADER,
    CardsEP.CROSSBOW_WILD,
    CardsEP.GENTLY_USED_KNAPSACK,
    CardsEP.ROOT_TEA_RED,
    CardsEP.SMUGGLERS_TRAIL,
    CardsEP.ROOT_TEA_YELLOW,
    CardsEP.A_VISIT_TO_FRIENDS,
    CardsEP.BAKE_SALE,
    CardsEP.INVESTMENTS,
    CardsEP.AMBUSH_RED,
    CardsEP.AMBUSH_YELLOW,
    CardsEP.AMBUSH_ORANGE,
    CardsEP.AMBUSH_WILD,
    CardsEP.AMBUSH_WILD,
]
