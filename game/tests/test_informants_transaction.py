from django.test import TestCase
from game.models.game_models import Faction, CraftedCardEntry, DiscardPileEntry, HandEntry, DeckEntry
from game.models.wa.turn import WABirdsong, WADaylight, WAEvening, WATurn
from game.models.events.event import Event, EventType
from game.models.events.crafted_cards import InformantsEvent
from game.transactions.crafted_cards.informants import use_informants, skip_informants
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.tests.my_factories import PlayerFactory, CardFactory, CraftedCardEntryFactory, DiscardPileEntryFactory, WATurnFactory
from rest_framework.exceptions import ValidationError

class InformantsTransactionTests(TestCase):
    def setup_wa_evening(self, player):
        game = player.game
        game.active_player_order = player.turn_order
        game.save()
        turn = WATurnFactory(player=player)
        
        # Advance to evening
        WABirdsong.objects.filter(turn=turn).update(step=WABirdsong.WABirdsongSteps.COMPLETED)
        WADaylight.objects.filter(turn=turn).update(step=WADaylight.WADaylightSteps.COMPLETED)
        WAEvening.objects.filter(turn=turn).update(step=WAEvening.WAEveningSteps.MILITARY_OPERATIONS)
        
        # Populate deck
        for i in range(5):
            card = CardFactory(game=game)
            DeckEntry.objects.create(game=game, card=card, spot=i)
            
        return turn

    def test_use_informants_success(self):
        player = PlayerFactory(faction=Faction.WOODLAND_ALLIANCE)
        self.setup_wa_evening(player)
        game = player.game
        
        # Setup card
        informants_card = CardFactory(game=game, card_type=CardsEP.INFORMANTS.name)
        crafted_card = CraftedCardEntryFactory(player=player, card=informants_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Setup ambush card in discard pile
        ambush_card = CardFactory(game=game, card_type=CardsEP.AMBUSH_RED.name)
        discard_entry = DiscardPileEntryFactory(game=game, card=ambush_card)
        
        # Setup event
        event = Event.objects.create(game=game, type=EventType.INFORMANTS)
        InformantsEvent.objects.create(event=event, crafted_card_entry=crafted_card)
        
        # Use informants
        use_informants(crafted_card, discard_entry)
        
        # Verify
        assert HandEntry.objects.filter(player=player, card=ambush_card).exists()
        assert not DiscardPileEntry.objects.filter(id=discard_entry.id).exists()
        crafted_card.refresh_from_db()
        assert crafted_card.used == CraftedCardEntry.UsedChoice.USED
        event.refresh_from_db()
        assert event.is_resolved == True

    def test_skip_informants_success(self):
        player = PlayerFactory(faction=Faction.WOODLAND_ALLIANCE)
        self.setup_wa_evening(player)
        game = player.game
        
        informants_card = CardFactory(game=game, card_type=CardsEP.INFORMANTS.name)
        crafted_card = CraftedCardEntryFactory(player=player, card=informants_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        event = Event.objects.create(game=game, type=EventType.INFORMANTS)
        InformantsEvent.objects.create(event=event, crafted_card_entry=crafted_card)
        
        skip_informants(crafted_card)
        
        crafted_card.refresh_from_db()
        assert crafted_card.used == CraftedCardEntry.UsedChoice.USED
        event.refresh_from_db()
        assert event.is_resolved == True

    def test_use_informants_fail_not_ambush(self):
        player = PlayerFactory(faction=Faction.WOODLAND_ALLIANCE)
        self.setup_wa_evening(player)
        game = player.game
        
        informants_card = CardFactory(game=game, card_type=CardsEP.INFORMANTS.name)
        crafted_card = CraftedCardEntryFactory(player=player, card=informants_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Non-ambush card
        not_ambush_card = CardFactory(game=game, card_type=CardsEP.SABOTEURS.name)
        discard_entry = DiscardPileEntryFactory(game=game, card=not_ambush_card)
        
        with self.assertRaises(ValueError) as cm:
            use_informants(crafted_card, discard_entry)
        self.assertIn("not an ambush card", str(cm.exception))
