from django.test import TestCase

from game.models.game_models import Faction, Warrior, HandEntry
from game.models.moles.turn import MoleDaylight, MoleTurn, MoleBirdsong
from game.models.moles.burrow import Burrow
from game.models.moles.ministers import Minister
from game.models.moles.crown import Crown
from game.tests.my_factories import MolesGameSetupFactory, CardFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.errors import UnavailableActionError, IllegalActionError
from game.transactions.moles.daylight.sway_minister import (
    end_sway_minister, sway_minister
)


class MolesSwayMinisterBaseTestCase(TestCase):
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

        # Set daylight to SWAY_MINISTER step
        self.daylight.step = MoleDaylight.MoleDaylightSteps.SWAY_MINISTER
        self.daylight.save()

        # Get burrow and starting clearing
        self.burrow = Burrow.objects.get(player=self.player)
        self.start_clearing = self.game.clearing_set.get(clearing_number=3)

        # Initialize all ministers as unswayed
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

    def place_moles_warriors_in_clearing(self, clearing, count=1):
        """Place Moles warriors in a clearing from supply."""
        for _ in range(count):
            warrior = Warrior.objects.filter(
                player=self.player, clearing__isnull=True
            ).first()
            if warrior:
                warrior.clearing = clearing
                warrior.save()


class MolesEndSwayMinisterTests(MolesSwayMinisterBaseTestCase):
    def test_end_sway_minister_advances_step(self):
        """end_sway_minister advances through BEFORE_END to COMPLETED."""
        end_sway_minister(self.player)

        self.daylight.refresh_from_db()
        # next_step calls step_effect which triggers another next_step at BEFORE_END
        self.assertEqual(self.daylight.step, MoleDaylight.MoleDaylightSteps.COMPLETED)

    def test_end_sway_minister_non_moles_raises(self):
        """end_sway_minister with non-Moles player raises UnavailableActionError."""
        birds_player = self.game.players.get(faction=Faction.BIRDS)
        self.game.current_turn = birds_player.turn_order
        self.game.save()

        with self.assertRaises(UnavailableActionError):
            end_sway_minister(birds_player)


class MolesSwayMarshalTests(MolesSwayMinisterBaseTestCase):
    """Test sway_minister for Marshal (Squire rank = 2 cards)."""

    def test_sway_marshal_happy_path(self):
        """Sway Marshal with 2 valid cards marks minister swayed, crown used, scores 1pt."""
        # Use WILD cards which match any clearing with moles pieces
        self.clear_hand()
        self.add_card_to_hand(CardsEP.AMBUSH_WILD)
        self.add_card_to_hand(CardsEP.CROSSBOW_WILD)

        initial_score = self.player.score

        sway_minister(
            self.player,
            Minister.MinisterName.MARSHAL,
            [CardsEP.AMBUSH_WILD, CardsEP.CROSSBOW_WILD],
        )

        # Marshal swayed
        marshal = Minister.objects.get(player=self.player, name=Minister.MinisterName.MARSHAL)
        self.assertTrue(marshal.swayed)

        # Crown used
        self.assertTrue(Crown.objects.filter(
            player=self.player, type=Crown.CrownType.SQUIRE, used=True
        ).exists())

        # Score increased by 1 (Squire tier)
        self.player.refresh_from_db()
        self.assertEqual(self.player.score, initial_score + 1)

        # Cards revealed (not in hand anymore)
        self.assertEqual(HandEntry.objects.filter(player=self.player).count(), 0)

        # Step advanced through SWAY_MINISTER → BEFORE_END → COMPLETED
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, MoleDaylight.MoleDaylightSteps.COMPLETED)

    def test_sway_minister_already_swayed_raises(self):
        """Sway marshal that's already swayed raises IllegalActionError."""
        marshal = Minister.objects.get(player=self.player, name=Minister.MinisterName.MARSHAL)
        marshal.swayed = True
        marshal.save()

        self.clear_hand()
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        with self.assertRaises(IllegalActionError):
            sway_minister(
                self.player,
                Minister.MinisterName.MARSHAL,
                [CardsEP.RABBIT_PARTISANS, CardsEP.RABBIT_PARTISANS],
            )

    def test_sway_minister_wrong_card_count_raises(self):
        """Sway Marshal with wrong number of cards raises IllegalActionError."""
        self.clear_hand()
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        with self.assertRaises(IllegalActionError):
            sway_minister(self.player, Minister.MinisterName.MARSHAL, [CardsEP.RABBIT_PARTISANS])


class MolesSwayBrigadierTests(MolesSwayMinisterBaseTestCase):
    """Test sway_minister for Brigadier (Noble rank = 3 cards)."""

    def test_sway_brigadier_scores_2_points(self):
        """Sway Brigadier (Noble) awards 2 points."""
        self.clear_hand()
        self.add_card_to_hand(CardsEP.AMBUSH_WILD)
        self.add_card_to_hand(CardsEP.CROSSBOW_WILD)
        self.add_card_to_hand(CardsEP.DOMINANCE_WILD)

        initial_score = self.player.score

        sway_minister(
            self.player,
            Minister.MinisterName.BRIGADIER,
            [
                CardsEP.AMBUSH_WILD,
                CardsEP.CROSSBOW_WILD,
                CardsEP.DOMINANCE_WILD,
            ],
        )

        self.player.refresh_from_db()
        self.assertEqual(self.player.score, initial_score + 2)

        # Crown used
        self.assertTrue(Crown.objects.filter(
            player=self.player, type=Crown.CrownType.NOBLE, used=True
        ).exists())


class MolesSwayDuchessTests(MolesSwayMinisterBaseTestCase):
    """Test sway_minister for Duchess of Mud (Lord rank = 4 cards)."""

    def test_sway_duchess_scores_3_points(self):
        """Sway Duchess of Mud (Lord) awards 3 points."""
        # Place warriors in 4 different clearings for card matching
        clearings_to_use = [
            self.game.clearing_set.get(clearing_number=2),  # mouse
            self.game.clearing_set.get(clearing_number=1),  # fox
            self.game.clearing_set.get(clearing_number=6),  # fox
            self.game.clearing_set.get(clearing_number=7),  # mouse
        ]
        for clearing in clearings_to_use:
            warrior = Warrior.objects.filter(player=self.player, clearing__isnull=True).first()
            if warrior:
                warrior.clearing = clearing
                warrior.save()

        self.clear_hand()
        # Use 3 wild cards + 1 RABBIT (clearing 3 has warriors from setup)
        self.add_card_to_hand(CardsEP.AMBUSH_WILD)
        self.add_card_to_hand(CardsEP.CROSSBOW_WILD)
        self.add_card_to_hand(CardsEP.DOMINANCE_WILD)
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        initial_score = self.player.score

        sway_minister(
            self.player,
            Minister.MinisterName.DUCHESS_OF_MUD,
            [
                CardsEP.AMBUSH_WILD,
                CardsEP.CROSSBOW_WILD,
                CardsEP.DOMINANCE_WILD,
                CardsEP.RABBIT_PARTISANS,
            ],
        )

        self.player.refresh_from_db()
        self.assertEqual(self.player.score, initial_score + 3)

        # Crown used
        self.assertTrue(Crown.objects.filter(
            player=self.player, type=Crown.CrownType.LORD, used=True
        ).exists())


class MolesSwayCardValidationTests(MolesSwayMinisterBaseTestCase):
    """Test sway_minister card clearing validation."""

    def test_sway_minister_card_clearing_validation(self):
        """Sway requires cards to match clearings with moles pieces."""
        # Setup: add warriors to different clearings so cards can match
        clearing_3 = self.start_clearing
        clearing_4 = self.game.clearing_set.get(clearing_number=4)
        clearing_6 = self.game.clearing_set.get(clearing_number=6)

        # Place moles warriors in clearings 3, 4
        self.place_moles_warriors_in_clearing(clearing_3)
        self.place_moles_warriors_in_clearing(clearing_4)

        self.clear_hand()
        # Add RABBIT cards (suit for clearing 3 and 4) and FOX (suit for clearing 6)
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        sway_minister(
            self.player,
            Minister.MinisterName.MARSHAL,
            [CardsEP.RABBIT_PARTISANS, CardsEP.RABBIT_PARTISANS],
        )

        marshal = Minister.objects.get(player=self.player, name=Minister.MinisterName.MARSHAL)
        self.assertTrue(marshal.swayed)

    def test_sway_minister_card_no_matching_clearing_raises(self):
        """Sway raises error if card suit doesn't match any clearing with moles pieces."""
        # Only place warriors in clearing 3 (RABBIT suit)
        self.clear_hand()
        # Try to use a FOX suit card but moles only in RABBIT clearing
        self.add_card_to_hand(CardsEP.AMBUSH_RED)  # FOX suit
        self.add_card_to_hand(CardsEP.AMBUSH_RED)

        with self.assertRaises(IllegalActionError):
            sway_minister(
                self.player,
                Minister.MinisterName.MARSHAL,
                [CardsEP.AMBUSH_RED, CardsEP.AMBUSH_RED],
            )


class MolesSwayWrongStepTests(MolesSwayMinisterBaseTestCase):
    def test_sway_minister_wrong_step_raises(self):
        """Sway in wrong step raises UnavailableActionError."""
        self.daylight.step = MoleDaylight.MoleDaylightSteps.ACTIONS
        self.daylight.save()

        self.clear_hand()
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        with self.assertRaises(UnavailableActionError):
            sway_minister(
                self.player,
                Minister.MinisterName.MARSHAL,
                [CardsEP.RABBIT_PARTISANS, CardsEP.RABBIT_PARTISANS],
            )
