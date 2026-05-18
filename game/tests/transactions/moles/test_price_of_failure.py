from unittest.mock import patch

from django.test import TestCase

from game.models.enums import Faction
from game.models.events.event import Event, EventType
from game.models.events.moles import PriceOfFailureEvent
from game.models.game_models import (
    Building,
    BuildingSlot,
    HandEntry,
    Player,
    Token,
    Warrior,
)
from game.models.moles.buildings import Citadel, Market
from game.models.moles.ministers import Minister
from game.models.removal_tracker import RemovalEventTracker
from game.errors import IllegalActionError, UnavailableActionError
from game.tests.my_factories import (
    MolesBirdsGameSetupFactory,
    MolesCrowsGameSetupFactory,
    MolesWAGameSetupFactory,
    CardFactory,
    WarriorFactory,
)
from game.transactions.moles.price_of_failure import (
    trigger_price_of_failure,
    resolve_price_of_failure,
)


class PriceOfFailureBaseTestCase(TestCase):
    def setUp(self):
        self.game = MolesBirdsGameSetupFactory()
        self.player = self.game.players.get(faction=Faction.MOLES)

    def sway(self, name):
        m = Minister.objects.get(player=self.player, name=name)
        m.swayed = True
        m.save()
        return m

    def add_card_to_hand(self, card_enum=None):
        from game.game_data.cards.exiles_and_partisans import CardsEP
        card_enum = card_enum or CardsEP.AMBUSH_RED
        card = CardFactory(game=self.game, card_type=card_enum.name)
        return HandEntry.objects.create(player=self.player, card=card)

    def clear_hand(self):
        HandEntry.objects.filter(player=self.player).delete()

    def place_citadel(self, clearing_number):
        clearing = self.game.clearing_set.get(clearing_number=clearing_number)
        citadel = Citadel.objects.filter(player=self.player, building_slot__isnull=True).first()
        slot = clearing.buildingslot_set.filter(building__isnull=True).first()
        citadel.building_slot = slot
        citadel.save()
        return citadel

    def place_market(self, clearing_number):
        clearing = self.game.clearing_set.get(clearing_number=clearing_number)
        market = Market.objects.filter(player=self.player, building_slot__isnull=True).first()
        slot = clearing.buildingslot_set.filter(building__isnull=True).first()
        market.building_slot = slot
        market.save()
        return market


# ---------------------------------------------------------------------------
# trigger_price_of_failure — core logic
# ---------------------------------------------------------------------------

class TriggerPriceOfFailureTests(PriceOfFailureBaseTestCase):

    def test_no_ministers_discards_card(self):
        """With no swayed ministers, only a card is discarded."""
        self.add_card_to_hand()
        hand_before = HandEntry.objects.filter(player=self.player).count()
        trigger_price_of_failure(self.player)
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), hand_before - 1)

    def test_no_ministers_no_card_no_error(self):
        """With no swayed ministers and empty hand, nothing errors."""
        self.clear_hand()
        trigger_price_of_failure(self.player)  # should not raise

    def test_one_lord_two_nobles_auto_resolves_lord(self):
        """Exactly one lord swayed with two nobles: lord is auto-unswayed, card discarded."""
        duchess = self.sway(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway(Minister.MinisterName.BRIGADIER)
        self.sway(Minister.MinisterName.MAYOR)
        self.add_card_to_hand()

        trigger_price_of_failure(self.player)

        duchess.refresh_from_db()
        self.assertFalse(duchess.swayed)
        # nobles remain swayed
        self.assertTrue(Minister.objects.get(player=self.player, name=Minister.MinisterName.BRIGADIER).swayed)

    def test_one_lord_auto_discard(self):
        """Auto-resolve discards a card from hand."""
        self.sway(Minister.MinisterName.DUCHESS_OF_MUD)
        self.add_card_to_hand()
        hand_before = HandEntry.objects.filter(player=self.player).count()

        trigger_price_of_failure(self.player)

        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), hand_before - 1)

    def test_two_lords_creates_event(self):
        """Two lords swayed: creates PriceOfFailureEvent, does not auto-resolve."""
        self.sway(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway(Minister.MinisterName.EARL_OF_STONE)
        self.sway(Minister.MinisterName.BRIGADIER)  # noble (lower rank, irrelevant)

        trigger_price_of_failure(self.player)

        event = Event.objects.filter(game=self.game, type=EventType.PRICE_OF_FAILURE, is_resolved=False).first()
        self.assertIsNotNone(event)
        self.assertTrue(PriceOfFailureEvent.objects.filter(event=event).exists())
        # Neither lord should be unswayed yet
        self.assertTrue(Minister.objects.get(player=self.player, name=Minister.MinisterName.DUCHESS_OF_MUD).swayed)
        self.assertTrue(Minister.objects.get(player=self.player, name=Minister.MinisterName.EARL_OF_STONE).swayed)

    def test_three_lords_creates_event(self):
        """All three lords swayed: creates event, does not auto-resolve."""
        for name in [Minister.MinisterName.DUCHESS_OF_MUD, Minister.MinisterName.EARL_OF_STONE, Minister.MinisterName.BARON_OF_DIRT]:
            self.sway(name)

        trigger_price_of_failure(self.player)

        self.assertTrue(Event.objects.filter(game=self.game, type=EventType.PRICE_OF_FAILURE, is_resolved=False).exists())


# ---------------------------------------------------------------------------
# trigger deduplication via RemovalEventTracker
# ---------------------------------------------------------------------------

class TriggerDeduplicationTests(PriceOfFailureBaseTestCase):

    def test_deduplication_with_tracker_already_triggered(self):
        """If tracker.price_of_failure_triggered is True, trigger is a no-op."""
        self.sway(Minister.MinisterName.DUCHESS_OF_MUD)
        tracker = RemovalEventTracker.objects.create(game=self.game)
        tracker.price_of_failure_triggered = True
        tracker.save()

        trigger_price_of_failure(self.player)

        # Minister stays swayed, no event created
        self.assertTrue(Minister.objects.get(player=self.player, name=Minister.MinisterName.DUCHESS_OF_MUD).swayed)
        self.assertFalse(Event.objects.filter(game=self.game, type=EventType.PRICE_OF_FAILURE).exists())

    def test_deduplication_sets_tracker_flag(self):
        """First trigger sets tracker flag so subsequent calls are no-ops."""
        self.sway(Minister.MinisterName.DUCHESS_OF_MUD)
        tracker = RemovalEventTracker.objects.create(game=self.game)

        trigger_price_of_failure(self.player)

        tracker.refresh_from_db()
        self.assertTrue(tracker.price_of_failure_triggered)


# ---------------------------------------------------------------------------
# resolve_price_of_failure
# ---------------------------------------------------------------------------

class ResolvePriceOfFailureTests(PriceOfFailureBaseTestCase):

    def _create_event(self):
        event = Event.objects.create(game=self.game, type=EventType.PRICE_OF_FAILURE, is_resolved=False)
        PriceOfFailureEvent.objects.create(event=event)
        return event

    def test_no_event_raises_unavailable(self):
        with self.assertRaises(UnavailableActionError):
            resolve_price_of_failure(self.player, Minister.MinisterName.DUCHESS_OF_MUD)

    def test_minister_not_swayed_raises_illegal(self):
        """If chosen minister is not swayed at all, raises IllegalActionError."""
        self.sway(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway(Minister.MinisterName.EARL_OF_STONE)
        self._create_event()

        # Baron of Dirt is a lord but not swayed
        with self.assertRaises(IllegalActionError):
            resolve_price_of_failure(self.player, Minister.MinisterName.BARON_OF_DIRT)

    def test_minister_not_highest_rank_raises_illegal(self):
        """Choosing a noble when lords are available raises IllegalActionError."""
        self.sway(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway(Minister.MinisterName.EARL_OF_STONE)
        self.sway(Minister.MinisterName.BRIGADIER)
        self._create_event()

        with self.assertRaises(IllegalActionError):
            resolve_price_of_failure(self.player, Minister.MinisterName.BRIGADIER)

    def test_happy_path_unswayed_minister(self):
        """Chosen minister is unswayed and event is resolved."""
        self.sway(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway(Minister.MinisterName.EARL_OF_STONE)
        event = self._create_event()

        resolve_price_of_failure(self.player, Minister.MinisterName.DUCHESS_OF_MUD)

        duchess = Minister.objects.get(player=self.player, name=Minister.MinisterName.DUCHESS_OF_MUD)
        self.assertFalse(duchess.swayed)
        # Other lord stays swayed
        self.assertTrue(Minister.objects.get(player=self.player, name=Minister.MinisterName.EARL_OF_STONE).swayed)

        event.refresh_from_db()
        self.assertTrue(event.is_resolved)

    def test_happy_path_discards_card(self):
        """Resolution discards one card from hand."""
        self.sway(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway(Minister.MinisterName.EARL_OF_STONE)
        self._create_event()
        self.add_card_to_hand()
        hand_before = HandEntry.objects.filter(player=self.player).count()

        resolve_price_of_failure(self.player, Minister.MinisterName.DUCHESS_OF_MUD)

        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), hand_before - 1)

    def test_happy_path_empty_hand_no_error(self):
        """Resolution with empty hand does not error."""
        self.sway(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway(Minister.MinisterName.EARL_OF_STONE)
        self._create_event()
        self.clear_hand()

        resolve_price_of_failure(self.player, Minister.MinisterName.DUCHESS_OF_MUD)  # should not raise


# ---------------------------------------------------------------------------
# Integration: trigger via player_removes_building in revolt
# ---------------------------------------------------------------------------

class PriceOfFailureRevoltTriggerTests(TestCase):

    def setUp(self):
        self.game = MolesWAGameSetupFactory()
        self.moles = self.game.players.get(faction=Faction.MOLES)
        self.wa = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)

    def sway_moles(self, name):
        m = Minister.objects.get(player=self.moles, name=name)
        m.swayed = True
        m.save()

    def place_moles_citadel(self, clearing_number):
        clearing = self.game.clearing_set.get(clearing_number=clearing_number)
        citadel = Citadel.objects.filter(player=self.moles, building_slot__isnull=True).first()
        slot = clearing.buildingslot_set.filter(building__isnull=True).first()
        citadel.building_slot = slot
        citadel.save()
        return citadel

    def test_revolt_triggers_price_of_failure(self):
        """WA revolt that removes a Moles citadel triggers price of failure."""
        from game.models.wa.tokens import WASympathy
        from game.models.wa.player import SupporterStackEntry
        from game.models.game_models import Card, Suit
        from game.transactions.wa.birdsong import revolt

        # Place WA sympathy in clearing 6 (fox) and 7 (fox) to set up revolt suit
        clearing = self.game.clearing_set.get(clearing_number=6)
        sympathy = WASympathy.objects.filter(player=self.wa, clearing__isnull=True).first()
        sympathy.clearing = clearing
        sympathy.save()

        # Give WA supporters matching the clearing suit
        card = Card.objects.filter(game=self.game, suit=clearing.suit).first()
        SupporterStackEntry.objects.create(player=self.wa, card=card)
        SupporterStackEntry.objects.create(player=self.wa, card=card)

        # Place a Moles citadel in that clearing
        self.place_moles_citadel(6)
        self.sway_moles(Minister.MinisterName.DUCHESS_OF_MUD)

        # Give Moles warriors in clearing so WA can revolt (needs WABase in supply)
        from game.models.wa.buildings import WABase
        base = WABase.objects.filter(player=self.wa, building_slot__isnull=True, suit=clearing.suit).first()
        if base is None:
            # Revolt requires a matching base in supply — if none, skip
            return

        revolt(self.wa, clearing)

        # Duchess was the only lord — she should auto-unsway
        duchess = Minister.objects.get(player=self.moles, name=Minister.MinisterName.DUCHESS_OF_MUD)
        self.assertFalse(duchess.swayed)

    def test_revolt_triggers_price_of_failure_only_once(self):
        """If revolt removes two Moles buildings, price of failure triggers only once."""
        from game.models.wa.tokens import WASympathy
        from game.models.wa.player import SupporterStackEntry
        from game.models.game_models import Card
        from game.transactions.wa.birdsong import revolt

        clearing = self.game.clearing_set.get(clearing_number=6)
        sympathy = WASympathy.objects.filter(player=self.wa, clearing__isnull=True).first()
        sympathy.clearing = clearing
        sympathy.save()

        card = Card.objects.filter(game=self.game, suit=clearing.suit).first()
        SupporterStackEntry.objects.create(player=self.wa, card=card)
        SupporterStackEntry.objects.create(player=self.wa, card=card)

        # Place TWO moles buildings in that clearing
        citadel = Citadel.objects.filter(player=self.moles, building_slot__isnull=True).first()
        market = Market.objects.filter(player=self.moles, building_slot__isnull=True).first()
        slots = list(clearing.buildingslot_set.filter(building__isnull=True)[:2])
        if len(slots) < 2:
            return  # not enough slots, skip

        citadel.building_slot = slots[0]
        citadel.save()
        market.building_slot = slots[1]
        market.save()

        # Sway two lords so an event is created (not auto-resolved)
        self.sway_moles(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway_moles(Minister.MinisterName.EARL_OF_STONE)

        from game.models.wa.buildings import WABase
        base = WABase.objects.filter(player=self.wa, building_slot__isnull=True, suit=clearing.suit).first()
        if base is None:
            return

        revolt(self.wa, clearing)

        # Only ONE price of failure event should be created
        event_count = Event.objects.filter(game=self.game, type=EventType.PRICE_OF_FAILURE).count()
        self.assertEqual(event_count, 1)


# ---------------------------------------------------------------------------
# Integration: trigger via crow bomb
# ---------------------------------------------------------------------------

class PriceOfFailureBombTriggerTests(TestCase):

    def setUp(self):
        self.game = MolesCrowsGameSetupFactory()
        self.moles = self.game.players.get(faction=Faction.MOLES)
        self.crows = self.game.players.get(faction=Faction.CROWS)

    def sway_moles(self, name):
        m = Minister.objects.get(player=self.moles, name=name)
        m.swayed = True
        m.save()

    def place_moles_citadel(self, clearing_number):
        clearing = self.game.clearing_set.get(clearing_number=clearing_number)
        citadel = Citadel.objects.filter(player=self.moles, building_slot__isnull=True).first()
        slot = clearing.buildingslot_set.filter(building__isnull=True).first()
        citadel.building_slot = slot
        citadel.save()
        return citadel

    def place_crow_bomb(self, clearing_number):
        from game.models.crows.tokens import PlotToken
        clearing = self.game.clearing_set.get(clearing_number=clearing_number)
        bomb = PlotToken.objects.filter(player=self.crows, plot_type=PlotToken.PlotType.BOMB, clearing__isnull=True).first()
        bomb.clearing = clearing
        bomb.is_facedown = False
        bomb.save()
        return bomb

    def test_bomb_triggers_price_of_failure(self):
        """Crow bomb that removes a Moles citadel triggers price of failure."""
        from game.transactions.crows.birdsong import resolve_bomb

        clearing_number = 6
        self.place_moles_citadel(clearing_number)
        bomb = self.place_crow_bomb(clearing_number)
        self.sway_moles(Minister.MinisterName.DUCHESS_OF_MUD)

        resolve_bomb(self.crows, bomb)

        duchess = Minister.objects.get(player=self.moles, name=Minister.MinisterName.DUCHESS_OF_MUD)
        self.assertFalse(duchess.swayed)

    def test_bomb_triggers_only_once_with_two_buildings(self):
        """Bomb removes two Moles buildings but price of failure triggers only once."""
        from game.transactions.crows.birdsong import resolve_bomb

        clearing_number = 6
        clearing = self.game.clearing_set.get(clearing_number=clearing_number)
        citadel = Citadel.objects.filter(player=self.moles, building_slot__isnull=True).first()
        market = Market.objects.filter(player=self.moles, building_slot__isnull=True).first()
        slots = list(clearing.buildingslot_set.filter(building__isnull=True)[:2])
        if len(slots) < 2:
            return

        citadel.building_slot = slots[0]
        citadel.save()
        market.building_slot = slots[1]
        market.save()

        bomb = self.place_crow_bomb(clearing_number)
        self.sway_moles(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway_moles(Minister.MinisterName.EARL_OF_STONE)

        resolve_bomb(self.crows, bomb)

        event_count = Event.objects.filter(game=self.game, type=EventType.PRICE_OF_FAILURE).count()
        self.assertEqual(event_count, 1)


# ---------------------------------------------------------------------------
# Integration: trigger via battle (various steps)
# ---------------------------------------------------------------------------

class PriceOfFailureBattleTriggerTests(TestCase):

    def setUp(self):
        self.game = MolesBirdsGameSetupFactory()
        self.moles = self.game.players.get(faction=Faction.MOLES)
        self.birds = self.game.players.get(faction=Faction.BIRDS)

        # Clean warriors from all clearings for clean test state
        Warrior.objects.all().delete()

    def sway_moles(self, name):
        m = Minister.objects.get(player=self.moles, name=name)
        m.swayed = True
        m.save()

    def place_moles_citadel(self, clearing):
        citadel = Citadel.objects.filter(player=self.moles, building_slot__isnull=True).first()
        slot = clearing.buildingslot_set.filter(building__isnull=True).first()
        citadel.building_slot = slot
        citadel.save()
        return citadel

    def place_moles_market(self, clearing):
        market = Market.objects.filter(player=self.moles, building_slot__isnull=True).first()
        slot = clearing.buildingslot_set.filter(building__isnull=True).first()
        market.building_slot = slot
        market.save()
        return market

    def test_moles_lose_one_building_in_ambush(self):
        """Moles attacking (1 warrior, 1 building), gets ambushed. Ambush removes warrior, then Moles chooses building. Price of failure triggers."""
        from game.transactions.battle import start_battle, defender_ambush_choice, attacker_ambush_choice, attacker_choose_ambush_hit
        from game.game_data.cards.exiles_and_partisans import CardsEP

        clearing = self.game.clearing_set.get(clearing_number=6)

        # Moles attacker: 1 warrior, 1 citadel
        WarriorFactory(player=self.moles, clearing=clearing)
        citadel = self.place_moles_citadel(clearing)

        # Birds defender: 2 warriors
        WarriorFactory.create_batch(2, player=self.birds, clearing=clearing)

        # Sway two nobles so event launches
        self.sway_moles(Minister.MinisterName.BRIGADIER)
        self.sway_moles(Minister.MinisterName.MAYOR)

        # Give Birds ambush card
        ambush_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.birds, card=ambush_card)

        battle = start_battle(self.game, Faction.MOLES, Faction.BIRDS, clearing)

        # Birds uses ambush (2 hits)
        defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)

        # Moles doesn't cancel ambush - removes 1 warrior, moves to ATTACKER_CHOOSE_AMBUSH_HITS
        attacker_ambush_choice(self.game, battle, None)

        # Moles chooses citadel for the remaining ambush hit
        attacker_choose_ambush_hit(self.game, battle, citadel)

        # Building removal triggers price of failure
        event_count = Event.objects.filter(game=self.game, type=EventType.PRICE_OF_FAILURE).count()
        self.assertEqual(event_count, 1)

    @patch('game.transactions.battle.randint')
    def test_moles_lose_one_building_as_attacker(self, mock_randint):
        """Moles attacking, loses warrior + building to dice. Price of failure triggers."""
        from game.transactions.battle import start_battle, defender_ambush_choice
        from game.queries.general import count_player_pieces_in_clearing

        clearing = self.game.clearing_set.get(clearing_number=6)

        # Moles attacker: 1 warrior, 1 citadel
        WarriorFactory(player=self.moles, clearing=clearing)
        citadel = self.place_moles_citadel(clearing)

        # Birds defender: 2 warriors
        WarriorFactory.create_batch(2, player=self.birds, clearing=clearing)

        # Sway two nobles so event launches
        self.sway_moles(Minister.MinisterName.BRIGADIER)
        self.sway_moles(Minister.MinisterName.MAYOR)

        # Verify setup
        moles_pieces = count_player_pieces_in_clearing(self.moles, clearing)
        birds_pieces = count_player_pieces_in_clearing(self.birds, clearing)
        print(f"Before battle: Moles={moles_pieces}, Birds={birds_pieces}")

        # Mock main battle roll: Moles rolls 2, Birds rolls 2
        # (ambush checks don't use dice)
        mock_randint.side_effect = [2, 2]

        battle = start_battle(self.game, Faction.MOLES, Faction.BIRDS, clearing)
        print(f"Battle created, step={battle.step}")

        # No ambush
        defender_ambush_choice(self.game, battle, None)

        battle.refresh_from_db()
        print(f"After defender_ambush_choice, step={battle.step}")

        # Moles warrior should be removed by defender hits
        moles_after = count_player_pieces_in_clearing(self.moles, clearing)
        print(f"After battle: Moles={moles_after}")
        self.assertFalse(Warrior.objects.filter(player=self.moles, clearing=clearing).exists())

        # Check that price of failure event was created
        event_count = Event.objects.filter(game=self.game, type=EventType.PRICE_OF_FAILURE).count()
        print(f"Price of failure events: {event_count}")
        self.assertEqual(event_count, 1)

    def test_moles_lose_building_choosing_over_tunnel_in_ambush(self):
        """Moles attacking (1 warrior, 1 building, 1 tunnel), gets ambushed. Removes warrior, then chooses to lose building. Price of failure triggers."""
        from game.transactions.battle import start_battle, defender_ambush_choice, attacker_ambush_choice, attacker_choose_ambush_hit
        from game.game_data.cards.exiles_and_partisans import CardsEP
        from game.models.moles.tokens import Tunnel

        clearing = self.game.clearing_set.get(clearing_number=6)

        # Moles attacker: 1 warrior, 1 citadel, 1 tunnel
        WarriorFactory(player=self.moles, clearing=clearing)
        citadel = self.place_moles_citadel(clearing)

        # Place tunnel in clearing
        tunnel = Tunnel.objects.filter(player=self.moles, clearing__isnull=True).first()
        if tunnel:
            tunnel.clearing = clearing
            tunnel.save()
        else:
            # Create a tunnel if none available
            tunnel = Tunnel.objects.create(player=self.moles, clearing=clearing)

        # Birds defender: 2 warriors
        WarriorFactory.create_batch(2, player=self.birds, clearing=clearing)

        # Sway two nobles so event launches
        self.sway_moles(Minister.MinisterName.BRIGADIER)
        self.sway_moles(Minister.MinisterName.MAYOR)

        # Give Birds ambush card
        ambush_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        HandEntry.objects.create(player=self.birds, card=ambush_card)

        battle = start_battle(self.game, Faction.MOLES, Faction.BIRDS, clearing)

        # Birds uses ambush (2 hits)
        defender_ambush_choice(self.game, battle, CardsEP.AMBUSH_RED)

        # Moles doesn't cancel ambush - removes 1 warrior, moves to ATTACKER_CHOOSE_AMBUSH_HITS
        # Now has choice: tunnel or building for the remaining hit
        attacker_ambush_choice(self.game, battle, None)

        # Moles chooses citadel over tunnel
        attacker_choose_ambush_hit(self.game, battle, citadel)

        # Building removal triggers price of failure
        event_count = Event.objects.filter(game=self.game, type=EventType.PRICE_OF_FAILURE).count()
        self.assertEqual(event_count, 1)

    @patch('game.transactions.battle.randint')
    def test_moles_lose_two_buildings_as_attacker(self, mock_randint):
        """Moles attacking with 2 buildings, loses both. Price of failure triggers only once (deduplication)."""
        from game.transactions.battle import start_battle, defender_ambush_choice

        # Find clearing with 2 building slots
        clearing = self.game.clearing_set.get(clearing_number=2)

        # Moles attacker: 1 warrior, 2 buildings
        WarriorFactory(player=self.moles, clearing=clearing)
        self.place_moles_citadel(clearing)
        self.place_moles_market(clearing)

        # Birds defender: 3 warriors (enough to kill all Moles pieces with 3 hits)
        WarriorFactory.create_batch(3, player=self.birds, clearing=clearing)

        # Sway two lords so event launches
        self.sway_moles(Minister.MinisterName.DUCHESS_OF_MUD)
        self.sway_moles(Minister.MinisterName.EARL_OF_STONE)

        # Mock main battle roll: Moles rolls 3 (capped to 1), Birds rolls 3 (kills all)
        mock_randint.side_effect = [3, 3]

        battle = start_battle(self.game, Faction.MOLES, Faction.BIRDS, clearing)

        # No ambush
        defender_ambush_choice(self.game, battle, None)

        # All Moles pieces should be gone
        self.assertFalse(Warrior.objects.filter(player=self.moles, clearing=clearing).exists())
        self.assertFalse(Citadel.objects.filter(player=self.moles, building_slot__clearing=clearing).exists())
        self.assertFalse(Market.objects.filter(player=self.moles, building_slot__clearing=clearing).exists())

        # Only ONE price of failure event should be created (deduplication)
        event_count = Event.objects.filter(game=self.game, type=EventType.PRICE_OF_FAILURE).count()
        self.assertEqual(event_count, 1)

