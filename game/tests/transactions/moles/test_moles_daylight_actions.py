from django.test import TestCase

from game.models.game_models import Faction, Warrior, HandEntry, Player
from game.models.moles.buildings import Citadel
from game.models.moles.turn import MoleDaylight, MoleTurn, MoleBirdsong
from game.models.moles.burrow import Burrow
from game.models.moles.tokens import Tunnel
from game.models.events.battle import Battle
from game.tests.my_factories import MolesGameSetupFactory, CardFactory, PlayerFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.errors import UnavailableActionError, IllegalActionError
from game.transactions.moles.daylight import (
    build, move, recruit, battle, dig, decrement_actions
)


class MolesDaylightActionBaseTestCase(TestCase):
    def setUp(self):
        self.game = MolesGameSetupFactory()
        self.player = self.game.players.get(faction=Faction.MOLES)

        # Set current player to Moles so turn creation works
        self.game.current_turn = self.player.turn_order
        self.game.save()

        # Create a turn for Moles
        self.turn = MoleTurn.create_turn(self.player)
        self.birdsong = self.turn.birdsong.first()
        self.daylight = self.turn.daylight.first()

        # Complete birdsong phase so get_phase returns daylight
        self.birdsong.step = MoleBirdsong.MoleBirdsongSteps.COMPLETED
        self.birdsong.save()

        # Set daylight to ACTIONS step
        self.daylight.step = MoleDaylight.MoleDaylightSteps.ACTIONS
        self.daylight.actions_left = 2
        self.daylight.save()

        # Get burrow and starting clearing (from setup, moles picked corner 3)
        self.burrow = Burrow.objects.get(player=self.player)
        self.start_clearing = self.game.clearing_set.get(clearing_number=3)

    def clear_hand(self):
        """Remove all cards from player hand."""
        HandEntry.objects.filter(player=self.player).delete()

    def add_card_to_hand(self, card_enum):
        """Add a specific card to player hand."""
        card = CardFactory(game=self.game, card_type=card_enum.name)
        HandEntry.objects.create(player=self.player, card=card)


class MolesBuildTests(MolesDaylightActionBaseTestCase):
    def test_build_places_building(self):
        """Build places citadel in a clearing player rules."""
        self.clear_hand()
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        initial_citadels = Citadel.objects.filter(
            player=self.player, building_slot__isnull=False
        ).count()

        # Build in start clearing (player has warriors there from setup)
        build(self.player, CardsEP.RABBIT_PARTISANS, "citadel", self.start_clearing)

        final_citadels = Citadel.objects.filter(
            player=self.player, building_slot__isnull=False
        ).count()

        # Citadel placed
        self.assertEqual(final_citadels, initial_citadels + 1)

        # Card no longer in hand
        self.assertFalse(HandEntry.objects.filter(player=self.player).exists())

        # Actions decremented
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 1)

    def test_build_unruled_clearing_raises(self):
        """Building in unruled clearing raises error."""
        from game.errors import IllegalActionError

        self.clear_hand()
        self.add_card_to_hand(CardsEP.AMBUSH_RED)

        # Get a clearing the player doesn't rule (no warriors there)
        unruled = self.game.clearing_set.exclude(clearing_number=3).first()

        with self.assertRaises(IllegalActionError):
            build(self.player, CardsEP.AMBUSH_RED, "citadel", unruled)


class MolesMoveTests(MolesDaylightActionBaseTestCase):
    def test_move_moves_warriors(self):
        """Move transfers warriors between adjacent clearings."""
        # Start with warriors in starting clearing (from setup)
        # Move to an adjacent clearing
        adjacent = self.start_clearing.connected_clearings.first()

        initial_start = Warrior.objects.filter(
            player=self.player, clearing=self.start_clearing
        ).count()
        initial_adj = Warrior.objects.filter(
            player=self.player, clearing=adjacent
        ).count()

        move(self.player, self.start_clearing, adjacent, 1)

        final_start = Warrior.objects.filter(
            player=self.player, clearing=self.start_clearing
        ).count()
        final_adj = Warrior.objects.filter(
            player=self.player, clearing=adjacent
        ).count()

        self.assertEqual(final_start, initial_start - 1)
        self.assertEqual(final_adj, initial_adj + 1)

        # Actions decremented
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 1)


class MolesRecruitTests(MolesDaylightActionBaseTestCase):
    def test_recruit_places_warrior_in_burrow(self):
        """Recruit places 1 warrior from supply to burrow."""
        initial_supply = Warrior.objects.filter(
            player=self.player, clearing__isnull=True
        ).count()
        initial_burrow = Warrior.objects.filter(
            player=self.player, clearing=self.burrow
        ).count()

        recruit(self.player)

        final_supply = Warrior.objects.filter(
            player=self.player, clearing__isnull=True
        ).count()
        final_burrow = Warrior.objects.filter(
            player=self.player, clearing=self.burrow
        ).count()

        self.assertEqual(final_supply, initial_supply - 1)
        self.assertEqual(final_burrow, initial_burrow + 1)

        # Actions decremented
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 1)


class MolesBattleTests(MolesDaylightActionBaseTestCase):
    def test_battle_starts_battle(self):
        """Battle initiates a battle in a clearing."""
        # Place a Birds warrior in start_clearing so battle can happen
        birds_player = self.game.players.get(faction=Faction.BIRDS)
        birds_warrior = Warrior.objects.filter(player=birds_player, clearing__isnull=True).first()
        if birds_warrior:
            birds_warrior.clearing = self.start_clearing
            birds_warrior.save()

        initial_battles = Battle.objects.filter(event__game=self.game).count()

        battle(self.player, Faction.BIRDS, self.start_clearing)

        final_battles = Battle.objects.filter(event__game=self.game).count()
        self.assertEqual(final_battles, initial_battles + 1)

        # Actions decremented
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 1)


class MolesDigTests(MolesDaylightActionBaseTestCase):
    def test_dig_places_tunnel_from_supply(self):
        """Dig places tunnel from supply and moves warriors."""
        # Place warriors in burrow for the dig action
        for _ in range(4):
            warrior = Warrior.objects.filter(
                player=self.player, clearing__isnull=True
            ).first()
            if warrior:
                warrior.clearing = self.burrow
                warrior.save()

        self.clear_hand()
        self.add_card_to_hand(CardsEP.AMBUSH_RED)

        # Get a clearing adjacent to start (for digging)
        dig_clearing = self.start_clearing.connected_clearings.first()

        initial_tunnels_supply = Tunnel.objects.filter(
            player=self.player, clearing__isnull=True
        ).count()
        initial_burrow = Warrior.objects.filter(
            player=self.player, clearing=self.burrow
        ).count()
        initial_dig_clearing = Warrior.objects.filter(
            player=self.player, clearing=dig_clearing
        ).count()

        dig(self.player, CardsEP.AMBUSH_RED, dig_clearing, warriors_to_move=2)

        final_tunnels_supply = Tunnel.objects.filter(
            player=self.player, clearing__isnull=True
        ).count()
        final_dig_clearing = Warrior.objects.filter(
            player=self.player, clearing=dig_clearing
        ).count()
        final_burrow = Warrior.objects.filter(
            player=self.player, clearing=self.burrow
        ).count()

        # Tunnel placed
        self.assertEqual(final_tunnels_supply, initial_tunnels_supply - 1)

        # Warriors moved
        self.assertEqual(final_dig_clearing, initial_dig_clearing + 2)
        self.assertEqual(final_burrow, initial_burrow - 2)

        # Card discarded
        self.assertFalse(HandEntry.objects.filter(player=self.player).exists())

        # Actions decremented
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 1)

    def test_dig_cant_move_more_than_four(self):
        """Dig with more than 4 warriors raises error."""
        from game.errors import IllegalActionError

        # Place enough warriors in burrow
        for _ in range(6):
            warrior = Warrior.objects.filter(
                player=self.player, clearing__isnull=True
            ).first()
            if warrior:
                warrior.clearing = self.burrow
                warrior.save()

        self.clear_hand()
        self.add_card_to_hand(CardsEP.AMBUSH_RED)

        dig_clearing = self.start_clearing.connected_clearings.first()

        with self.assertRaises(IllegalActionError):
            dig(self.player, CardsEP.AMBUSH_RED, dig_clearing, warriors_to_move=5)

    def test_dig_not_enough_warriors_raises(self):
        """Dig requesting more warriors than available raises error."""
        from game.errors import IllegalActionError

        self.clear_hand()
        self.add_card_to_hand(CardsEP.AMBUSH_RED)

        dig_clearing = self.start_clearing.connected_clearings.first()

        # Only 1 warrior in burrow initially (from birdsong)
        with self.assertRaises(IllegalActionError):
            dig(self.player, CardsEP.AMBUSH_RED, dig_clearing, warriors_to_move=4)


class MolesActionsLeftTests(MolesDaylightActionBaseTestCase):
    def test_actions_left_reaches_zero_advances_step(self):
        """When actions_left reaches 0, step advances to MINISTER_ACTIONS."""
        self.daylight.actions_left = 1
        self.daylight.save()

        # Do any action that decrements
        recruit(self.player)

        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)


class MolesDaylightTimingTests(MolesDaylightActionBaseTestCase):
    def test_build_wrong_step_raises(self):
        """Build in wrong step raises UnavailableActionError."""
        self.clear_hand()
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        # Move to wrong step
        self.daylight.step = MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS
        self.daylight.save()

        with self.assertRaises(UnavailableActionError):
            build(self.player, CardsEP.RABBIT_PARTISANS, "citadel", self.start_clearing)

    def test_move_wrong_step_raises(self):
        """Move in wrong step raises UnavailableActionError."""
        self.daylight.step = MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS
        self.daylight.save()

        adjacent = self.start_clearing.connected_clearings.first()
        with self.assertRaises(UnavailableActionError):
            move(self.player, self.start_clearing, adjacent, 1)

    def test_recruit_wrong_step_raises(self):
        """Recruit in wrong step raises UnavailableActionError."""
        self.daylight.step = MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS
        self.daylight.save()

        with self.assertRaises(UnavailableActionError):
            recruit(self.player)

    def test_battle_wrong_step_raises(self):
        """Battle in wrong step raises UnavailableActionError."""
        self.daylight.step = MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS
        self.daylight.save()

        with self.assertRaises(UnavailableActionError):
            battle(self.player, Faction.BIRDS, self.start_clearing)

    def test_dig_wrong_step_raises(self):
        """Dig in wrong step raises UnavailableActionError."""
        self.clear_hand()
        self.add_card_to_hand(CardsEP.AMBUSH_RED)

        self.daylight.step = MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS
        self.daylight.save()

        dig_clearing = self.start_clearing.connected_clearings.first()
        with self.assertRaises(UnavailableActionError):
            dig(self.player, CardsEP.AMBUSH_RED, dig_clearing, warriors_to_move=1)


class MolesDaylightFactionTests(TestCase):
    def setUp(self):
        self.game = MolesGameSetupFactory()
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.moles_player = self.game.players.get(faction=Faction.MOLES)

        # Create a Moles turn
        self.moles_turn = MoleTurn.create_turn(self.moles_player)
        self.daylight = MoleDaylight.objects.get(turn=self.moles_turn)
        self.daylight.step = MoleDaylight.MoleDaylightSteps.ACTIONS
        self.daylight.save()

    def test_build_non_moles_player_raises(self):
        """Build with non-Moles player raises UnavailableActionError."""
        # Make it Birds player's turn
        self.game.current_turn = self.birds_player.turn_order
        self.game.save()

        with self.assertRaises(UnavailableActionError):
            build(self.birds_player, CardsEP.RABBIT_PARTISANS, "citadel",
                  self.game.clearing_set.get(clearing_number=1))

    def test_recruit_non_moles_player_raises(self):
        """Recruit with non-Moles player raises UnavailableActionError."""
        self.game.current_turn = self.birds_player.turn_order
        self.game.save()

        with self.assertRaises(UnavailableActionError):
            recruit(self.birds_player)

    def test_move_non_moles_player_raises(self):
        """Move with non-Moles player raises UnavailableActionError."""
        self.game.current_turn = self.birds_player.turn_order
        self.game.save()

        c1 = self.game.clearing_set.get(clearing_number=1)
        c5 = self.game.clearing_set.get(clearing_number=5)
        with self.assertRaises(UnavailableActionError):
            move(self.birds_player, c1, c5, 1)
