from django.test import TestCase

from game.models.game_models import Faction, Warrior, HandEntry
from game.models.moles.buildings import Citadel, Market
from game.models.moles.turn import MoleDaylight, MoleTurn, MoleBirdsong
from game.models.moles.burrow import Burrow
from game.models.moles.tokens import Tunnel
from game.models.moles.ministers import Minister
from game.models.events.battle import Battle
from game.tests.my_factories import MolesGameSetupFactory, CardFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.errors import UnavailableActionError, IllegalActionError
from game.transactions.moles.daylight.minister_actions import (
    use_marshal, use_captain, use_foremole, use_banker,
    use_duchess, use_baron, use_earl, check_all_ministers_used,
    end_minister_actions, skip_brigadier, use_brigadier, use_mayor
)


class MolesMinisterActionBaseTestCase(TestCase):
    def setUp(self):
        self.game = MolesGameSetupFactory()
        self.player = self.game.players.get(faction=Faction.MOLES)

        # Set current player to Moles
        self.game.current_turn = self.player.turn_order
        self.game.save()

        # Create a turn for Moles
        self.turn = MoleTurn.create_turn(self.player)
        self.birdsong = MoleBirdsong.objects.get(turn=self.turn)
        self.daylight = MoleDaylight.objects.get(turn=self.turn)

        # Complete birdsong phase
        self.birdsong.step = MoleBirdsong.MoleBirdsongSteps.COMPLETED
        self.birdsong.save()

        # Set daylight to MINISTER_ACTIONS step
        self.daylight.step = MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS
        self.daylight.save()

        # Get burrow and starting clearing
        self.burrow = Burrow.objects.get(player=self.player)
        self.start_clearing = self.game.clearing_set.get(clearing_number=3)

        # Mark ministers as already swayed for testing use_ functions
        # (use_ functions assume ministers are already swayed)
        for minister in Minister.objects.filter(player=self.player):
            minister.swayed = False
            minister.used = False
            minister.save()

    def clear_hand(self):
        """Remove all cards from player hand."""
        HandEntry.objects.filter(player=self.player).delete()

    def add_card_to_hand(self, card_enum):
        """Add a specific card to player hand."""
        card = CardFactory(game=self.game, card_type=card_enum.name)
        HandEntry.objects.create(player=self.player, card=card)

    def sway_minister_for_test(self, minister_name):
        """Mark a minister as swayed for testing use_ functions."""
        minister = Minister.objects.get(player=self.player, name=minister_name)
        minister.swayed = True
        minister.used = False
        minister.save()


class MolesMarshalTests(MolesMinisterActionBaseTestCase):
    def test_use_marshal_moves_warriors(self):
        """Marshal moves warriors between clearings."""
        self.sway_minister_for_test(Minister.MinisterName.MARSHAL)

        adjacent = self.start_clearing.connected_clearings.first()
        initial_start = Warrior.objects.filter(
            player=self.player, clearing=self.start_clearing
        ).count()
        initial_adj = Warrior.objects.filter(
            player=self.player, clearing=adjacent
        ).count()

        use_marshal(self.player, self.start_clearing, adjacent, 1)

        final_start = Warrior.objects.filter(
            player=self.player, clearing=self.start_clearing
        ).count()
        final_adj = Warrior.objects.filter(
            player=self.player, clearing=adjacent
        ).count()

        self.assertEqual(final_start, initial_start - 1)
        self.assertEqual(final_adj, initial_adj + 1)

        marshal = Minister.objects.get(player=self.player, name=Minister.MinisterName.MARSHAL)
        self.assertTrue(marshal.used)


class MolesCaptainTests(MolesMinisterActionBaseTestCase):
    def test_use_captain_starts_battle(self):
        """Captain starts a battle in a clearing."""
        self.sway_minister_for_test(Minister.MinisterName.CAPTAIN)

        birds_player = self.game.players.get(faction=Faction.BIRDS)
        birds_warrior = Warrior.objects.filter(player=birds_player, clearing__isnull=True).first()
        if birds_warrior:
            birds_warrior.clearing = self.start_clearing
            birds_warrior.save()

        initial_battles = Battle.objects.filter(event__game=self.game).count()

        use_captain(self.player, Faction.BIRDS, self.start_clearing)

        final_battles = Battle.objects.filter(event__game=self.game).count()
        self.assertEqual(final_battles, initial_battles + 1)

        captain = Minister.objects.get(player=self.player, name=Minister.MinisterName.CAPTAIN)
        self.assertTrue(captain.used)


class MolesForemoleTests(MolesMinisterActionBaseTestCase):
    def test_use_foremole_builds_any_clearing(self):
        """Foremole builds in any clearing player rules, no suit requirement."""
        self.sway_minister_for_test(Minister.MinisterName.FOREMOLE)

        self.clear_hand()
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        initial_citadels = Citadel.objects.filter(
            player=self.player, building_slot__isnull=False
        ).count()

        use_foremole(self.player, CardsEP.RABBIT_PARTISANS, self.start_clearing, "citadel")

        final_citadels = Citadel.objects.filter(
            player=self.player, building_slot__isnull=False
        ).count()
        self.assertEqual(final_citadels, initial_citadels + 1)

        foremole = Minister.objects.get(player=self.player, name=Minister.MinisterName.FOREMOLE)
        self.assertTrue(foremole.used)


class MolesBankerTests(MolesMinisterActionBaseTestCase):
    def test_use_banker_scores_points(self):
        """Banker scores 1 point per card of matching suit."""
        self.sway_minister_for_test(Minister.MinisterName.BANKER)

        self.clear_hand()
        for _ in range(3):
            self.add_card_to_hand(CardsEP.AMBUSH_RED)

        initial_score = self.player.score

        cards_list = [CardsEP.AMBUSH_RED, CardsEP.AMBUSH_RED, CardsEP.AMBUSH_RED]
        use_banker(self.player, cards_list)

        self.player.refresh_from_db()
        self.assertEqual(self.player.score, initial_score + 3)

        banker = Minister.objects.get(player=self.player, name=Minister.MinisterName.BANKER)
        self.assertTrue(banker.used)

    def test_use_banker_mixed_suits_raises(self):
        """Banker with mixed suits raises error."""
        self.sway_minister_for_test(Minister.MinisterName.BANKER)

        self.clear_hand()
        self.add_card_to_hand(CardsEP.AMBUSH_RED)
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        with self.assertRaises(IllegalActionError):
            use_banker(self.player, [CardsEP.AMBUSH_RED, CardsEP.RABBIT_PARTISANS])


class MolesDuchessTests(MolesMinisterActionBaseTestCase):
    def test_use_duchess_scores_if_all_tunnels_on_map(self):
        """Duchess scores 2 points if all 3 tunnels are on map."""
        self.sway_minister_for_test(Minister.MinisterName.DUCHESS_OF_MUD)

        clearings = [
            self.game.clearing_set.get(clearing_number=6),
            self.game.clearing_set.get(clearing_number=7),
            self.game.clearing_set.get(clearing_number=11),
        ]
        tunnels = Tunnel.objects.filter(player=self.player, clearing__isnull=True)[:3]
        for i, tunnel in enumerate(tunnels):
            tunnel.clearing = clearings[i]
            tunnel.save()

        initial_score = self.player.score

        use_duchess(self.player)

        self.player.refresh_from_db()
        self.assertEqual(self.player.score, initial_score + 2)

        duchess = Minister.objects.get(player=self.player, name=Minister.MinisterName.DUCHESS_OF_MUD)
        self.assertTrue(duchess.used)

    def test_use_duchess_no_score_if_tunnel_in_supply(self):
        """Duchess doesn't score if any tunnel is in supply."""
        self.sway_minister_for_test(Minister.MinisterName.DUCHESS_OF_MUD)

        # Setup already placed 1 tunnel in corner clearing, so 2 are left in supply
        # Place only 1 more to leave 1 in supply
        clearing = self.game.clearing_set.get(clearing_number=6)
        tunnel = Tunnel.objects.filter(player=self.player, clearing__isnull=True).first()
        if tunnel:
            tunnel.clearing = clearing
            tunnel.save()

        initial_score = self.player.score

        use_duchess(self.player)

        self.player.refresh_from_db()
        self.assertEqual(self.player.score, initial_score)


class MolesBaronTests(MolesMinisterActionBaseTestCase):
    def test_use_baron_scores_per_market(self):
        """Baron scores 1 point per market on map."""
        self.sway_minister_for_test(Minister.MinisterName.BARON_OF_DIRT)

        clearings = [
            self.game.clearing_set.get(clearing_number=6),
            self.game.clearing_set.get(clearing_number=7),
        ]
        markets = Market.objects.filter(player=self.player, building_slot__isnull=True)[:2]
        for i, market in enumerate(markets):
            slot = clearings[i].buildingslot_set.first()
            market.building_slot = slot
            market.save()

        initial_score = self.player.score

        use_baron(self.player)

        self.player.refresh_from_db()
        self.assertEqual(self.player.score, initial_score + 2)

        baron = Minister.objects.get(player=self.player, name=Minister.MinisterName.BARON_OF_DIRT)
        self.assertTrue(baron.used)


class MolesEarlTests(MolesMinisterActionBaseTestCase):
    def test_use_earl_scores_per_citadel(self):
        """Earl scores 1 point per citadel on map."""
        self.sway_minister_for_test(Minister.MinisterName.EARL_OF_STONE)

        clearings = [
            self.game.clearing_set.get(clearing_number=6),
            self.game.clearing_set.get(clearing_number=7),
            self.game.clearing_set.get(clearing_number=11),
        ]
        citadels = Citadel.objects.filter(player=self.player, building_slot__isnull=True)[:3]
        for i, citadel in enumerate(citadels):
            slot = clearings[i].buildingslot_set.first()
            citadel.building_slot = slot
            citadel.save()

        initial_score = self.player.score

        use_earl(self.player)

        self.player.refresh_from_db()
        self.assertEqual(self.player.score, initial_score + 3)

        earl = Minister.objects.get(player=self.player, name=Minister.MinisterName.EARL_OF_STONE)
        self.assertTrue(earl.used)


class MolesAllMinistersUsedTests(MolesMinisterActionBaseTestCase):
    def test_check_all_ministers_used_advances_step(self):
        """When all swayed ministers are used, step advances."""
        self.sway_minister_for_test(Minister.MinisterName.MARSHAL)

        marshal = Minister.objects.get(player=self.player, name=Minister.MinisterName.MARSHAL)
        marshal.used = True
        marshal.save()

        check_all_ministers_used(self.player)

        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, MoleDaylight.MoleDaylightSteps.SWAY_MINISTER)

    def test_check_all_ministers_used_does_not_advance_if_unused_remain(self):
        """If any swayed minister is unused, step doesn't advance."""
        self.sway_minister_for_test(Minister.MinisterName.MARSHAL)

        initial_step = self.daylight.step

        check_all_ministers_used(self.player)

        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, initial_step)


class MolesMinisterTimingTests(MolesMinisterActionBaseTestCase):
    def test_use_marshal_wrong_step_raises(self):
        """Marshal in wrong step raises UnavailableActionError."""
        self.sway_minister_for_test(Minister.MinisterName.MARSHAL)

        self.daylight.step = MoleDaylight.MoleDaylightSteps.ACTIONS
        self.daylight.save()

        adjacent = self.start_clearing.connected_clearings.first()
        with self.assertRaises(UnavailableActionError):
            use_marshal(self.player, self.start_clearing, adjacent, 1)

    def test_use_captain_wrong_step_raises(self):
        """Captain in wrong step raises UnavailableActionError."""
        self.sway_minister_for_test(Minister.MinisterName.CAPTAIN)

        self.daylight.step = MoleDaylight.MoleDaylightSteps.ACTIONS
        self.daylight.save()

        with self.assertRaises(UnavailableActionError):
            use_captain(self.player, Faction.BIRDS, self.start_clearing)

    def test_use_banker_wrong_step_raises(self):
        """Banker in wrong step raises UnavailableActionError."""
        self.sway_minister_for_test(Minister.MinisterName.BANKER)

        self.daylight.step = MoleDaylight.MoleDaylightSteps.ACTIONS
        self.daylight.save()

        with self.assertRaises(UnavailableActionError):
            use_banker(self.player, [CardsEP.AMBUSH_RED])


class MolesMinisterFactionTests(TestCase):
    def setUp(self):
        self.game = MolesGameSetupFactory()
        self.birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.moles_player = self.game.players.get(faction=Faction.MOLES)

        # Create a Moles turn
        self.moles_turn = MoleTurn.create_turn(self.moles_player)
        self.daylight = MoleDaylight.objects.get(turn=self.moles_turn)
        self.daylight.step = MoleDaylight.MoleDaylightSteps.MINISTER_ACTIONS
        self.daylight.save()

    def test_use_marshal_non_moles_player_raises(self):
        """Marshal with non-Moles player raises UnavailableActionError."""
        self.game.current_turn = self.birds_player.turn_order
        self.game.save()

        c1 = self.game.clearing_set.get(clearing_number=1)
        c5 = self.game.clearing_set.get(clearing_number=5)
        with self.assertRaises(UnavailableActionError):
            use_marshal(self.birds_player, c1, c5, 1)

    def test_use_captain_non_moles_player_raises(self):
        """Captain with non-Moles player raises UnavailableActionError."""
        self.game.current_turn = self.birds_player.turn_order
        self.game.save()

        with self.assertRaises(UnavailableActionError):
            use_captain(self.birds_player, Faction.MOLES,
                       self.game.clearing_set.get(clearing_number=1))

    def test_use_banker_non_moles_player_raises(self):
        """Banker with non-Moles player raises UnavailableActionError."""
        self.game.current_turn = self.birds_player.turn_order
        self.game.save()

        with self.assertRaises(UnavailableActionError):
            use_banker(self.birds_player, [CardsEP.AMBUSH_RED])


class MolesEndMinisterActionsTests(MolesMinisterActionBaseTestCase):
    def test_end_minister_actions_advances_step(self):
        """end_minister_actions advances from MINISTER_ACTIONS step."""
        end_minister_actions(self.player)

        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, MoleDaylight.MoleDaylightSteps.SWAY_MINISTER)

    def test_end_minister_actions_non_moles_raises(self):
        """end_minister_actions with non-Moles player raises UnavailableActionError."""
        birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.game.current_turn = birds_player.turn_order
        self.game.save()

        with self.assertRaises(UnavailableActionError):
            end_minister_actions(birds_player)


class MolesSkipBrigadierTests(MolesMinisterActionBaseTestCase):
    def test_skip_brigadier_resets_action(self):
        """skip_brigadier resets brigadier_action to NONE."""
        self.daylight.brigadier_action = MoleDaylight.BrigadierAction.BATTLE
        self.daylight.save()

        skip_brigadier(self.player)

        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.brigadier_action, MoleDaylight.BrigadierAction.NONE)

    def test_skip_brigadier_when_none_raises(self):
        """skip_brigadier when no action in progress raises IllegalActionError."""
        self.daylight.brigadier_action = MoleDaylight.BrigadierAction.NONE
        self.daylight.save()

        with self.assertRaises(IllegalActionError):
            skip_brigadier(self.player)


class MolesBrigadierStateMachineTests(MolesMinisterActionBaseTestCase):
    def test_brigadier_move_then_battle_raises(self):
        """Brigadier action: if first was move, can't do battle."""
        # Sway multiple ministers so step doesn't advance after first action
        self.sway_minister_for_test(Minister.MinisterName.BRIGADIER)
        self.sway_minister_for_test(Minister.MinisterName.MARSHAL)

        # First move
        adjacent = self.start_clearing.connected_clearings.first()
        use_brigadier(self.player, "move", self.start_clearing, adjacent, 1)

        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.brigadier_action, MoleDaylight.BrigadierAction.MOVE)

        # Try to do battle next - should raise
        with self.assertRaises(IllegalActionError):
            use_brigadier(self.player, "battle", Faction.BIRDS, self.start_clearing)

    def test_brigadier_battle_then_move_raises(self):
        """Brigadier action: if first was battle, can't do move."""
        # Sway multiple ministers so step doesn't advance after first action
        self.sway_minister_for_test(Minister.MinisterName.BRIGADIER)
        self.sway_minister_for_test(Minister.MinisterName.MARSHAL)

        # Setup birds warrior for battle
        birds_player = self.game.players.get(faction=Faction.BIRDS)
        birds_warrior = Warrior.objects.filter(player=birds_player, clearing__isnull=True).first()
        assert birds_warrior is not None
        birds_warrior.clearing = self.start_clearing
        birds_warrior.save()

        # First battle
        use_brigadier(self.player, "battle", Faction.BIRDS, self.start_clearing)

        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.brigadier_action, MoleDaylight.BrigadierAction.BATTLE)

        # Try to do move next - should raise
        adjacent = self.start_clearing.connected_clearings.first()
        with self.assertRaises(IllegalActionError):
            use_brigadier(self.player, "move", self.start_clearing, adjacent, 1)

    def test_brigadier_two_moves_resets_state(self):
        """Brigadier can do same action twice; second call resets state."""
        # Sway multiple ministers so step doesn't advance after first action
        self.sway_minister_for_test(Minister.MinisterName.BRIGADIER)
        self.sway_minister_for_test(Minister.MinisterName.MARSHAL)

        adjacent = self.start_clearing.connected_clearings.first()
        another = adjacent.connected_clearings.exclude(clearing_number=self.start_clearing.clearing_number).first()
        assert another is not None

        # First move
        use_brigadier(self.player, "move", self.start_clearing, adjacent, 1)

        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.brigadier_action, MoleDaylight.BrigadierAction.MOVE)

        # Second move
        use_brigadier(self.player, "move", adjacent, another, 1)

        # State should reset to NONE after second action
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.brigadier_action, MoleDaylight.BrigadierAction.NONE)

    def test_brigadier_two_battles_resets_state(self):
        """Brigadier can do battle twice; second call resets state."""
        # Sway multiple ministers so step doesn't advance after first action
        self.sway_minister_for_test(Minister.MinisterName.BRIGADIER)
        self.sway_minister_for_test(Minister.MinisterName.MARSHAL)

        # Place birds warriors in two clearings
        birds_player = self.game.players.get(faction=Faction.BIRDS)
        birds_warriors = list(Warrior.objects.filter(player=birds_player, clearing__isnull=True)[:2])
        clearing_1 = self.start_clearing
        clearing_2 = self.start_clearing.connected_clearings.first()
        assert clearing_2 is not None

        assert len(birds_warriors) >= 2
        birds_warriors[0].clearing = clearing_1
        birds_warriors[0].save()
        birds_warriors[1].clearing = clearing_2
        birds_warriors[1].save()

        # First battle
        use_brigadier(self.player, "battle", Faction.BIRDS, clearing_1)

        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.brigadier_action, MoleDaylight.BrigadierAction.BATTLE)

        # Second battle
        use_brigadier(self.player, "battle", Faction.BIRDS, clearing_2)

        # State should reset to NONE after second action
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.brigadier_action, MoleDaylight.BrigadierAction.NONE)


class MolesBrigadierUsedFlagTests(MolesMinisterActionBaseTestCase):
    def test_brigadier_marked_used_only_on_first_call(self):
        """Brigadier is marked used only on first action, not on second."""
        # Sway multiple ministers so step doesn't advance after first action
        self.sway_minister_for_test(Minister.MinisterName.BRIGADIER)
        self.sway_minister_for_test(Minister.MinisterName.MARSHAL)

        adjacent = self.start_clearing.connected_clearings.first()
        another = adjacent.connected_clearings.exclude(clearing_number=self.start_clearing.clearing_number).first()
        assert another is not None

        # First action
        use_brigadier(self.player, "move", self.start_clearing, adjacent, 1)

        brigadier = Minister.objects.get(player=self.player, name=Minister.MinisterName.BRIGADIER)
        self.assertTrue(brigadier.used)

        # Reset flag (should stay reset for second action)
        brigadier.used = False
        brigadier.save()

        # Second action
        use_brigadier(self.player, "move", adjacent, another, 1)

        # Should still be False (not marked used again)
        brigadier.refresh_from_db()
        self.assertFalse(brigadier.used)


class MolesMayorErrorCasesTests(MolesMinisterActionBaseTestCase):
    def test_mayor_unswayed_minister_raises(self):
        """Mayor copying unswayed minister raises IllegalActionError."""
        self.sway_minister_for_test(Minister.MinisterName.MAYOR)

        # Leave Marshal unswayed
        marshal = Minister.objects.get(player=self.player, name=Minister.MinisterName.MARSHAL)
        marshal.swayed = False
        marshal.save()

        adjacent = self.start_clearing.connected_clearings.first()

        with self.assertRaises(IllegalActionError):
            use_mayor(self.player, Minister.MinisterName.MARSHAL, self.start_clearing, adjacent, 1)

    def test_mayor_cannot_copy_lords(self):
        """Mayor cannot copy lord-rank ministers."""
        self.sway_minister_for_test(Minister.MinisterName.MAYOR)

        # Sway Duchess but Mayor should reject it
        duchess = Minister.objects.get(player=self.player, name=Minister.MinisterName.DUCHESS_OF_MUD)
        duchess.swayed = True
        duchess.save()

        with self.assertRaises(IllegalActionError):
            use_mayor(self.player, Minister.MinisterName.DUCHESS_OF_MUD)


class MolesMayorCopiesMarshalTests(MolesMinisterActionBaseTestCase):
    def test_mayor_copies_marshal(self):
        """Mayor can copy Marshal's move action."""
        self.sway_minister_for_test(Minister.MinisterName.MAYOR)
        self.sway_minister_for_test(Minister.MinisterName.MARSHAL)

        adjacent = self.start_clearing.connected_clearings.first()
        initial_start = Warrior.objects.filter(
            player=self.player, clearing=self.start_clearing
        ).count()

        use_mayor(self.player, Minister.MinisterName.MARSHAL, self.start_clearing, adjacent, 1)

        mayor = Minister.objects.get(player=self.player, name=Minister.MinisterName.MAYOR)
        self.assertTrue(mayor.used)

        # Marshal should NOT be marked used (Mayor action doesn't use the copied minister)
        marshal = Minister.objects.get(player=self.player, name=Minister.MinisterName.MARSHAL)
        self.assertFalse(marshal.used)

        # Warriors should be moved
        final_start = Warrior.objects.filter(
            player=self.player, clearing=self.start_clearing
        ).count()
        self.assertEqual(final_start, initial_start - 1)


class MolesMayorCopiesCaptainTests(MolesMinisterActionBaseTestCase):
    def test_mayor_copies_captain(self):
        """Mayor can copy Captain's battle action."""
        self.sway_minister_for_test(Minister.MinisterName.MAYOR)
        self.sway_minister_for_test(Minister.MinisterName.CAPTAIN)

        # Place birds warrior for battle
        birds_player = self.game.players.get(faction=Faction.BIRDS)
        birds_warrior = Warrior.objects.filter(player=birds_player, clearing__isnull=True).first()
        assert birds_warrior is not None
        birds_warrior.clearing = self.start_clearing
        birds_warrior.save()

        initial_battles = Battle.objects.filter(event__game=self.game).count()

        use_mayor(self.player, Minister.MinisterName.CAPTAIN, Faction.BIRDS, self.start_clearing)

        final_battles = Battle.objects.filter(event__game=self.game).count()
        self.assertEqual(final_battles, initial_battles + 1)

        mayor = Minister.objects.get(player=self.player, name=Minister.MinisterName.MAYOR)
        self.assertTrue(mayor.used)


class MolesMayorCopiesForemoleTests(MolesMinisterActionBaseTestCase):
    def test_mayor_copies_foremole(self):
        """Mayor can copy Foremole's build action."""
        self.sway_minister_for_test(Minister.MinisterName.MAYOR)
        self.sway_minister_for_test(Minister.MinisterName.FOREMOLE)

        self.clear_hand()
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        initial_citadels = Citadel.objects.filter(
            player=self.player, building_slot__isnull=False
        ).count()

        use_mayor(self.player, Minister.MinisterName.FOREMOLE, CardsEP.RABBIT_PARTISANS, self.start_clearing, "citadel")

        final_citadels = Citadel.objects.filter(
            player=self.player, building_slot__isnull=False
        ).count()
        self.assertEqual(final_citadels, initial_citadels + 1)

        mayor = Minister.objects.get(player=self.player, name=Minister.MinisterName.MAYOR)
        self.assertTrue(mayor.used)


class MolesMayorCopiesBrigadierTests(MolesMinisterActionBaseTestCase):
    def test_mayor_copies_brigadier_move(self):
        """Mayor can copy Brigadier's move action."""
        self.sway_minister_for_test(Minister.MinisterName.MAYOR)
        self.sway_minister_for_test(Minister.MinisterName.BRIGADIER)

        adjacent = self.start_clearing.connected_clearings.first()
        initial_start = Warrior.objects.filter(
            player=self.player, clearing=self.start_clearing
        ).count()

        use_mayor(self.player, Minister.MinisterName.BRIGADIER, "move", self.start_clearing, adjacent, 1)

        mayor = Minister.objects.get(player=self.player, name=Minister.MinisterName.MAYOR)
        self.assertTrue(mayor.used)

        # Warriors should be moved
        final_start = Warrior.objects.filter(
            player=self.player, clearing=self.start_clearing
        ).count()
        self.assertEqual(final_start, initial_start - 1)

    def test_mayor_copies_brigadier_battle(self):
        """Mayor can copy Brigadier's battle action."""
        self.sway_minister_for_test(Minister.MinisterName.MAYOR)
        self.sway_minister_for_test(Minister.MinisterName.BRIGADIER)

        # Place birds warrior for battle
        birds_player = self.game.players.get(faction=Faction.BIRDS)
        birds_warrior = Warrior.objects.filter(player=birds_player, clearing__isnull=True).first()
        assert birds_warrior is not None
        birds_warrior.clearing = self.start_clearing
        birds_warrior.save()

        initial_battles = Battle.objects.filter(event__game=self.game).count()

        use_mayor(self.player, Minister.MinisterName.BRIGADIER, "battle", Faction.BIRDS, self.start_clearing)

        final_battles = Battle.objects.filter(event__game=self.game).count()
        self.assertEqual(final_battles, initial_battles + 1)

        mayor = Minister.objects.get(player=self.player, name=Minister.MinisterName.MAYOR)
        self.assertTrue(mayor.used)


class MolesMayorCopiesBankerTests(MolesMinisterActionBaseTestCase):
    def test_mayor_copies_banker(self):
        """Mayor can copy Banker's craft action."""
        self.sway_minister_for_test(Minister.MinisterName.MAYOR)
        self.sway_minister_for_test(Minister.MinisterName.BANKER)

        self.clear_hand()
        for _ in range(3):
            self.add_card_to_hand(CardsEP.AMBUSH_RED)

        initial_score = self.player.score

        use_mayor(self.player, Minister.MinisterName.BANKER, [CardsEP.AMBUSH_RED, CardsEP.AMBUSH_RED, CardsEP.AMBUSH_RED])

        self.player.refresh_from_db()
        self.assertEqual(self.player.score, initial_score + 3)

        mayor = Minister.objects.get(player=self.player, name=Minister.MinisterName.MAYOR)
        self.assertTrue(mayor.used)
