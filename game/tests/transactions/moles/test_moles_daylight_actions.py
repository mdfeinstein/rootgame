from django.test import TestCase

from game.models.game_models import Faction, Warrior, HandEntry
from game.models.moles.buildings import Citadel, Market
from game.models.moles.turn import MoleDaylight, MoleTurn, MoleBirdsong
from game.models.moles.burrow import Burrow
from game.tests.my_factories import MolesGameSetupFactory, CardFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
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

        # Get burrow
        self.burrow = Burrow.objects.get(player=self.player)

    def set_daylight_step(self, step):
        """Helper to set daylight step."""
        self.daylight.step = step
        self.daylight.save()

    def place_warriors_in_clearing(self, clearing, count):
        """Helper to place warriors in a clearing."""
        for _ in range(count):
            warrior = Warrior.objects.filter(player=self.player, clearing__isnull=True).first()
            if warrior:
                warrior.clearing = clearing
                warrior.save()


class MolesBuildTests(MolesDaylightActionBaseTestCase):
    def test_build_places_building(self):
        """Build places citadel/market in matching ruled clearing."""
        c2 = self.game.clearing_set.get(clearing_number=2)

        # Place warrior to rule the clearing
        self.place_warriors_in_clearing(c2, 1)

        # Remove all hand cards except one Fox card
        HandEntry.objects.filter(player=self.player).delete()
        fox_card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        HandEntry.objects.create(player=self.player, card=fox_card)

        initial_citadels_placed = Citadel.objects.filter(
            player=self.player, building_slot__isnull=False
        ).count()

        build(self.player, CardsEP.FOX_PARTISANS, "citadel", c2)

        final_citadels_placed = Citadel.objects.filter(
            player=self.player, building_slot__isnull=False
        ).count()
        self.assertEqual(final_citadels_placed, initial_citadels_placed + 1)

        # Card should be revealed
        self.assertFalse(HandEntry.objects.filter(player=self.player, card=fox_card).exists())

        # Actions should be decremented
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 1)

    def test_build_wrong_suit_raises(self):
        """Building with wrong suit card raises error."""
        c2 = self.game.clearing_set.get(clearing_number=2)
        self.place_warriors_in_clearing(c2, 1)

        HandEntry.objects.filter(player=self.player).delete()
        rabbit_card = CardFactory(game=self.game, card_type=CardsEP.RABBIT_PARTISANS.name)
        HandEntry.objects.create(player=self.player, card=rabbit_card)

        from game.errors import IllegalActionError
        with self.assertRaises(IllegalActionError):
            build(self.player, CardsEP.RABBIT_PARTISANS, "citadel", c2)

    def test_build_unruled_clearing_raises(self):
        """Building in unruled clearing raises error."""
        c5 = self.game.clearing_set.get(clearing_number=5)

        HandEntry.objects.filter(player=self.player).delete()
        fox_card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        HandEntry.objects.create(player=self.player, card=fox_card)

        from game.errors import IllegalActionError
        with self.assertRaises(IllegalActionError):
            build(self.player, CardsEP.FOX_PARTISANS, "citadel", c5)


class MolesMoveTests(MolesDaylightActionBaseTestCase):
    def test_move_moves_warriors(self):
        """Move transfers warriors between adjacent clearings."""
        c1 = self.game.clearing_set.get(clearing_number=1)
        c2 = self.game.clearing_set.get(clearing_number=2)

        # Place 3 warriors in c1
        self.place_warriors_in_clearing(c1, 3)

        initial_c1 = Warrior.objects.filter(player=self.player, clearing=c1).count()
        initial_c2 = Warrior.objects.filter(player=self.player, clearing=c2).count()

        move(self.player, c1, c2, 2)

        final_c1 = Warrior.objects.filter(player=self.player, clearing=c1).count()
        final_c2 = Warrior.objects.filter(player=self.player, clearing=c2).count()

        self.assertEqual(final_c1, initial_c1 - 2)
        self.assertEqual(final_c2, initial_c2 + 2)

        # Actions should be decremented
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 1)


class MolesRecruitTests(MolesDaylightActionBaseTestCase):
    def test_recruit_places_warrior_in_burrow(self):
        """Recruit places 1 warrior from supply to burrow."""
        initial_supply = Warrior.objects.filter(player=self.player, clearing__isnull=True).count()
        initial_burrow = Warrior.objects.filter(player=self.player, clearing=self.burrow).count()

        recruit(self.player)

        final_supply = Warrior.objects.filter(player=self.player, clearing__isnull=True).count()
        final_burrow = Warrior.objects.filter(player=self.player, clearing=self.burrow).count()

        self.assertEqual(final_supply, initial_supply - 1)
        self.assertEqual(final_burrow, initial_burrow + 1)

        # Actions should be decremented
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 1)


class MolesBattleTests(MolesDaylightActionBaseTestCase):
    def test_battle_starts_battle(self):
        """Battle initiates a battle in a clearing."""
        from game.models.game_models import Battle
        c2 = self.game.clearing_set.get(clearing_number=2)

        self.place_warriors_in_clearing(c2, 1)

        initial_battles = Battle.objects.filter(game=self.game).count()

        battle(self.player, Faction.CATS, c2)

        final_battles = Battle.objects.filter(game=self.game).count()
        self.assertEqual(final_battles, initial_battles + 1)

        # Actions should be decremented
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 1)


class MolesDigTests(MolesDaylightActionBaseTestCase):
    def test_dig_places_tunnel_from_supply(self):
        """Dig places tunnel from supply and moves warriors."""
        from game.models.moles.tokens import Tunnel

        c2 = self.game.clearing_set.get(clearing_number=2)
        self.place_warriors_in_clearing(c2, 1)

        # Place 6 warriors in burrow
        for _ in range(6):
            warrior = Warrior.objects.filter(player=self.player, clearing__isnull=True).first()
            warrior.clearing = self.burrow
            warrior.save()

        # Remove all hand cards except one Fox card
        HandEntry.objects.filter(player=self.player).delete()
        fox_card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        HandEntry.objects.create(player=self.player, card=fox_card)

        initial_tunnels_supply = Tunnel.objects.filter(
            player=self.player, clearing__isnull=True
        ).count()
        initial_burrow = Warrior.objects.filter(player=self.player, clearing=self.burrow).count()

        dig(self.player, CardsEP.FOX_PARTISANS, c2, warriors_to_move=4)

        final_tunnels_supply = Tunnel.objects.filter(
            player=self.player, clearing__isnull=True
        ).count()
        final_c2 = Warrior.objects.filter(player=self.player, clearing=c2).count()
        final_burrow = Warrior.objects.filter(player=self.player, clearing=self.burrow).count()

        # Tunnel placed
        self.assertEqual(final_tunnels_supply, initial_tunnels_supply - 1)

        # Warriors moved
        self.assertEqual(final_c2, 4)
        self.assertEqual(final_burrow, initial_burrow - 4)

        # Card discarded
        self.assertFalse(HandEntry.objects.filter(player=self.player, card=fox_card).exists())

        # Actions decremented
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_left, 1)

    def test_dig_cant_move_more_than_four(self):
        """Dig with more than 4 warriors raises error."""
        from game.errors import IllegalActionError

        c2 = self.game.clearing_set.get(clearing_number=2)
        self.place_warriors_in_clearing(c2, 1)

        # Place 6 warriors in burrow
        for _ in range(6):
            warrior = Warrior.objects.filter(player=self.player, clearing__isnull=True).first()
            warrior.clearing = self.burrow
            warrior.save()

        HandEntry.objects.filter(player=self.player).delete()
        fox_card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        HandEntry.objects.create(player=self.player, card=fox_card)

        with self.assertRaises(IllegalActionError):
            dig(self.player, CardsEP.FOX_PARTISANS, c2, warriors_to_move=5)

    def test_dig_moves_tunnel(self):
        """Dig can move tunnel from one clearing to another."""
        from game.models.moles.tokens import Tunnel

        c1 = self.game.clearing_set.get(clearing_number=1)  # Has tunnel from setup
        c2 = self.game.clearing_set.get(clearing_number=2)
        self.place_warriors_in_clearing(c2, 1)

        # Place 6 warriors in burrow
        for _ in range(6):
            warrior = Warrior.objects.filter(player=self.player, clearing__isnull=True).first()
            warrior.clearing = self.burrow
            warrior.save()

        HandEntry.objects.filter(player=self.player).delete()
        fox_card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        HandEntry.objects.create(player=self.player, card=fox_card)

        dig(self.player, CardsEP.FOX_PARTISANS, c2, warriors_to_move=2, clearing_to_move_tunnel_from=c1)

        # Tunnel moved from c1 to c2
        self.assertFalse(Tunnel.objects.filter(player=self.player, clearing=c1).exists())
        self.assertTrue(Tunnel.objects.filter(player=self.player, clearing=c2).exists())

    def test_dig_all_tunnels_no_tunnel_to_move_specified(self):
        """Dig with all tunnels on map and no move source raises error."""
        from game.errors import IllegalActionError

        c2 = self.game.clearing_set.get(clearing_number=2)
        c3 = self.game.clearing_set.get(clearing_number=3)
        c4 = self.game.clearing_set.get(clearing_number=4)

        self.place_warriors_in_clearing(c2, 1)

        # Place all tunnels on map
        from game.models.moles.tokens import Tunnel
        tunnels = Tunnel.objects.filter(player=self.player, clearing__isnull=True)
        tunnels[0].clearing = c3
        tunnels[0].save()
        tunnels[1].clearing = c4
        tunnels[1].save()

        # Place 4 warriors in burrow
        for _ in range(4):
            warrior = Warrior.objects.filter(player=self.player, clearing__isnull=True).first()
            warrior.clearing = self.burrow
            warrior.save()

        HandEntry.objects.filter(player=self.player).delete()
        fox_card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        HandEntry.objects.create(player=self.player, card=fox_card)

        with self.assertRaises(IllegalActionError):
            dig(self.player, CardsEP.FOX_PARTISANS, c2, warriors_to_move=2)

    def test_dig_not_enough_warriors_raises(self):
        """Dig requesting more warriors than available raises error."""
        from game.errors import IllegalActionError

        c2 = self.game.clearing_set.get(clearing_number=2)
        self.place_warriors_in_clearing(c2, 1)

        # Only 1 warrior in burrow
        HandEntry.objects.filter(player=self.player).delete()
        fox_card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        HandEntry.objects.create(player=self.player, card=fox_card)

        with self.assertRaises(IllegalActionError):
            dig(self.player, CardsEP.FOX_PARTISANS, c2, warriors_to_move=4)


class MolesActionsLeftTests(MolesDaylightActionBaseTestCase):
    def test_actions_left_reaches_zero_advances_step(self):
        """When actions_left reaches 0, step advances to MINISTER_ACTIONS."""
        self.daylight.actions_left = 1
        self.daylight.save()

        c1 = self.game.clearing_set.get(clearing_number=1)
        c2 = self.game.clearing_set.get(clearing_number=2)
        self.place_warriors_in_clearing(c1, 2)

        move(self.player, c1, c2, 1)

        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS)
