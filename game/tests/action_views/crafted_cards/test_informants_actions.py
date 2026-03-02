from django.test import TestCase
from django.contrib.auth.models import User
from game.models.game_models import Faction, CraftedCardEntry, Card, Clearing, HandEntry, Warrior, DiscardPileEntry, DeckEntry
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.tests.my_factories import (
    GameSetupWithFactionsFactory, CardFactory, CraftedCardEntryFactory,
    DiscardPileEntryFactory, WATurnFactory, UserFactory
)
from game.tests.client import RootGameClient
from game.models.events.crafted_cards import InformantsEvent
from game.models.wa.turn import WAEvening

class TestActionViews(TestCase):
    def setUp(self):
        # Create user with password for RootGameClient login
        self.username = "test_user"
        self.password = "password"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        
        # Use Factory to setup the game completely
        u1 = UserFactory()
        u2 = UserFactory()
        self.game = GameSetupWithFactionsFactory(
            factions=[Faction.CATS, Faction.BIRDS, Faction.WOODLAND_ALLIANCE],
            owner=self.user,
            users=[u1, u2, self.user] # WA at index 2 getting self.user
        )
        self.wa_player = self.game.players.get(faction=Faction.WOODLAND_ALLIANCE)
        
        # Initialize RootGameClient
        self.root_client = RootGameClient(user=self.username, password=self.password, game_id=self.game.pk)

    def setup_wa_evening(self, game):
        # Set turn to WA
        game.current_turn = self.wa_player.turn_order
        game.active_player_order = self.wa_player.turn_order
        game.save()
        
        # Mark setup as completed (GameSetupWithFactionsFactory should have done this, but let's be sure)
        from game.models.events.setup import GameSimpleSetup
        GameSimpleSetup.objects.filter(game=game).update(status=GameSimpleSetup.GameSetupStatus.COMPLETED)
        
        turn = WATurnFactory(player=self.wa_player)
        from game.models.wa.turn import WABirdsong, WADaylight, WAEvening
        WABirdsong.objects.filter(turn=turn).update(step=WABirdsong.WABirdsongSteps.COMPLETED)
        WADaylight.objects.filter(turn=turn).update(step=WADaylight.WADaylightSteps.COMPLETED)
        WAEvening.objects.filter(turn=turn).update(step=WAEvening.WAEveningSteps.DRAWING)
        
        # Populate deck
        for i in range(10):
            card = CardFactory(game=game)
            DeckEntry.objects.create(game=game, card=card, spot=i)
            
        return turn

    def test_informants_view_flow_use(self):
         # Setup WA and evening
        turn = self.setup_wa_evening(self.game)
        
        # Keep hand size below 5 (GameSetupFactory might have given some cards, let's clear them)
        HandEntry.objects.filter(player=self.wa_player).delete()
        
        # Setup Informants
        informants_card = CardFactory(game=self.game, card_type=CardsEP.INFORMANTS.name)
        CraftedCardEntryFactory(player=self.wa_player, card=informants_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        from game.transactions.crafted_cards.informants import informants_check
        informants_check(self.wa_player)
        
        # Setup Ambush in discard
        ambush_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        discard_entry = DiscardPileEntryFactory(game=self.game, card=ambush_card)
        
        # Initialize action
        self.root_client.get_action()
        self.assertEqual(self.root_client.step['name'], 'use_or_skip')
        
        # Step 1: Use Informants
        self.root_client.submit_action({"choice": "use"})
        self.assertEqual(self.root_client.step['name'], 'pick_ambush_card')
        
        # Step 2: Pick ambush card
        # This will trigger drawing. hand size is small, so it will complete everything.
        
        self.root_client.submit_action({"card": ambush_card.card_type})
            
        # Verify effects
        self.assertTrue(HandEntry.objects.filter(player=self.wa_player, card=ambush_card).exists())
        self.assertFalse(DiscardPileEntry.objects.filter(id=discard_entry.id).exists())
        
        evening = WAEvening.objects.get(turn=turn)
        self.assertEqual(evening.step, WAEvening.WAEveningSteps.COMPLETED)

    def test_informants_view_flow_skip(self):
        # Setup WA and evening
        turn = self.setup_wa_evening(self.game)
        
        # Setup Informants
        informants_card = CardFactory(game=self.game, card_type=CardsEP.INFORMANTS.name)
        crafted_entry = CraftedCardEntryFactory(player=self.wa_player, card=informants_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        from game.transactions.crafted_cards.informants import informants_check
        informants_check(self.wa_player)
        
        # Initialize action
        self.root_client.get_action()
        self.assertEqual(self.root_client.step['name'], 'use_or_skip')
        
        # Step 1: Skip Informants
        self.root_client.submit_action({"choice": "skip"})
            
        # Verify effects
        crafted_entry.refresh_from_db()
        self.assertEqual(crafted_entry.used, CraftedCardEntry.UsedChoice.USED)
        # Event should be resolved
        self.assertFalse(InformantsEvent.objects.filter(crafted_card_entry=crafted_entry, event__is_resolved=False).exists())
        
        evening = WAEvening.objects.get(turn=turn)
        self.assertEqual(evening.step, WAEvening.WAEveningSteps.COMPLETED)
