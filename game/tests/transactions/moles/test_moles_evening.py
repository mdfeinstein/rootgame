from django.test import TestCase

from game.models.game_models import Faction, HandEntry, RevealedCardEntry
from game.models.moles.turn import MoleEvening, MoleTurn, MoleBirdsong, MoleDaylight
from game.models.moles.buildings import Market, Citadel
from game.models.moles.ministers import Minister
from game.tests.my_factories import MolesGameSetupFactory, CardFactory
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.errors import UnavailableActionError
from game.transactions.moles.evening import (
    process_revealed_cards, draw_cards, discard_card
)
from game.transactions.moles.turn import reset_moles_turn


class MolesEveningBaseTestCase(TestCase):
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
        self.evening = MoleEvening.objects.get(turn=self.turn)

        # Complete birdsong and daylight phases
        self.birdsong.step = MoleBirdsong.MoleBirdsongSteps.COMPLETED
        self.birdsong.save()

        self.daylight.step = MoleDaylight.MoleDaylightSteps.COMPLETED
        self.daylight.save()

        # Start at PROCESS_REVEALED_CARDS
        self.evening.step = MoleEvening.MoleEveningSteps.PROCESS_REVEALED_CARDS
        self.evening.save()

    def clear_hand(self):
        """Remove all cards from player hand."""
        HandEntry.objects.filter(player=self.player).delete()

    def add_card_to_hand(self, card_enum):
        """Add a specific card to player hand."""
        card = CardFactory(game=self.game, card_type=card_enum.name)
        HandEntry.objects.create(player=self.player, card=card)

    def add_card_to_revealed(self, card_enum):
        """Add a card to revealed cards."""
        card = CardFactory(game=self.game, card_type=card_enum.name)
        RevealedCardEntry.objects.create(player=self.player, card=card)


class MolesProcessRevealedCardsTests(MolesEveningBaseTestCase):
    def test_process_revealed_wild_cards_go_to_discard(self):
        """Wild cards are moved to discard (removed from revealed)."""
        self.add_card_to_revealed(CardsEP.AMBUSH_WILD)

        initial_revealed = RevealedCardEntry.objects.filter(player=self.player).count()
        self.assertEqual(initial_revealed, 1)

        process_revealed_cards(self.player)

        final_revealed = RevealedCardEntry.objects.filter(player=self.player).count()
        self.assertEqual(final_revealed, 0)

    def test_process_revealed_non_wild_cards_go_to_hand(self):
        """Non-wild cards are moved back to hand."""
        self.clear_hand()
        self.add_card_to_revealed(CardsEP.RABBIT_PARTISANS)

        initial_hand = HandEntry.objects.filter(player=self.player).count()
        self.assertEqual(initial_hand, 0)

        process_revealed_cards(self.player)

        final_hand = HandEntry.objects.filter(player=self.player).count()
        self.assertEqual(final_hand, 1)

        final_revealed = RevealedCardEntry.objects.filter(player=self.player).count()
        self.assertEqual(final_revealed, 0)

    def test_process_revealed_wrong_step_raises(self):
        """process_revealed_cards at wrong step raises error."""
        self.evening.step = MoleEvening.MoleEveningSteps.CRAFT
        self.evening.save()

        self.add_card_to_revealed(CardsEP.AMBUSH_WILD)

        with self.assertRaises(Exception):
            process_revealed_cards(self.player)


class MolesDrawCardsTests(MolesEveningBaseTestCase):
    def setUp(self):
        super().setUp()
        self.evening.step = MoleEvening.MoleEveningSteps.DRAW
        self.evening.save()

    def test_draw_cards_base_1_plus_markets(self):
        """Draw 1 base + 1 per market on map."""
        # Place 1 market on map in an empty slot
        clearing = self.game.clearing_set.get(clearing_number=1)
        # Find an empty building slot
        empty_slot = clearing.buildingslot_set.filter(building__isnull=True).first()
        if not empty_slot:
            # If all slots are full, use a different clearing
            clearing = self.game.clearing_set.get(clearing_number=2)
            empty_slot = clearing.buildingslot_set.filter(building__isnull=True).first()

        market = Market.objects.filter(player=self.player, building_slot__isnull=True).first()
        assert market is not None
        market.building_slot = empty_slot
        market.save()

        self.clear_hand()
        initial_hand = HandEntry.objects.filter(player=self.player).count()

        draw_cards(self.player)

        final_hand = HandEntry.objects.filter(player=self.player).count()
        # Should draw 2 cards (1 base + 1 market)
        self.assertEqual(final_hand - initial_hand, 2)

    def test_draw_cards_wrong_step_raises(self):
        """draw_cards at wrong step raises error."""
        self.evening.step = MoleEvening.MoleEveningSteps.CRAFT
        self.evening.save()

        with self.assertRaises(Exception):
            draw_cards(self.player)


class MolesDiscardCardTests(MolesEveningBaseTestCase):
    def setUp(self):
        super().setUp()
        self.evening.step = MoleEvening.MoleEveningSteps.DISCARD
        self.evening.save()

    def test_discard_card_7_to_6_stays_in_discard(self):
        """Discard from 7 cards leaves 6, stays in DISCARD step."""
        self.clear_hand()
        for _ in range(7):
            self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        card_to_discard = HandEntry.objects.filter(player=self.player).first()
        assert card_to_discard is not None
        initial_step = self.evening.step

        discard_card(self.player, card_to_discard)

        self.evening.refresh_from_db()
        self.assertEqual(self.evening.step, initial_step)

        hand_size = HandEntry.objects.filter(player=self.player).count()
        self.assertEqual(hand_size, 6)

    def test_discard_card_6_to_5_advances_step(self):
        """Discard from 6 cards leaves 5, advances from DISCARD step."""
        self.clear_hand()
        for _ in range(6):
            self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        card_to_discard = HandEntry.objects.filter(player=self.player).first()
        assert card_to_discard is not None
        initial_step = self.evening.step

        discard_card(self.player, card_to_discard)

        self.evening.refresh_from_db()
        self.assertNotEqual(self.evening.step, initial_step)

        hand_size = HandEntry.objects.filter(player=self.player).count()
        self.assertEqual(hand_size, 5)

    def test_discard_card_hand_already_5_raises(self):
        """Discard when hand is already 5 raises error."""
        self.clear_hand()
        for _ in range(5):
            self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)

        card = HandEntry.objects.filter(player=self.player).first()
        assert card is not None

        with self.assertRaises(UnavailableActionError):
            discard_card(self.player, card)

    def test_discard_card_wrong_step_raises(self):
        """discard_card at wrong step raises error."""
        self.evening.step = MoleEvening.MoleEveningSteps.CRAFT
        self.evening.save()

        self.clear_hand()
        self.add_card_to_hand(CardsEP.RABBIT_PARTISANS)
        card = HandEntry.objects.filter(player=self.player).first()
        assert card is not None

        with self.assertRaises(Exception):
            discard_card(self.player, card)


class MolesResetMinisterTests(TestCase):
    def setUp(self):
        self.game = MolesGameSetupFactory()
        self.player = self.game.players.get(faction=Faction.MOLES)

        self.game.current_turn = self.player.turn_order
        self.game.save()

        self.turn = MoleTurn.create_turn(self.player)

    def test_reset_moles_turn_ministers_used_false(self):
        """reset_moles_turn sets all ministers used=False."""
        marshal = Minister.objects.get(player=self.player, name=Minister.MinisterName.MARSHAL)
        captain = Minister.objects.get(player=self.player, name=Minister.MinisterName.CAPTAIN)

        marshal.used = True
        captain.used = True
        marshal.save()
        captain.save()

        reset_moles_turn(self.player)

        for minister in Minister.objects.filter(player=self.player):
            self.assertFalse(minister.used)

    def test_reset_moles_turn_buildings_crafted_with_false(self):
        """reset_moles_turn sets all buildings crafted_with=False."""
        citadel = Citadel.objects.filter(player=self.player).first()
        market = Market.objects.filter(player=self.player).first()

        citadel.crafted_with = True
        market.crafted_with = True
        citadel.save()
        market.save()

        reset_moles_turn(self.player)

        for c in Citadel.objects.filter(player=self.player):
            self.assertFalse(c.crafted_with)
        for m in Market.objects.filter(player=self.player):
            self.assertFalse(m.crafted_with)

    def test_reset_moles_turn_brigadier_action_none(self):
        """reset_moles_turn sets brigadier_action to NONE."""
        daylight = MoleDaylight.objects.get(turn=self.turn)
        daylight.brigadier_action = MoleDaylight.BrigadierAction.BATTLE
        daylight.save()

        reset_moles_turn(self.player)

        daylight.refresh_from_db()
        self.assertEqual(daylight.brigadier_action, MoleDaylight.BrigadierAction.NONE)
