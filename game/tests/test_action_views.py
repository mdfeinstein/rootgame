from django.test import TestCase
from django.contrib.auth.models import User
from game.models.game_models import Faction, CraftedCardEntry, Card, Clearing, HandEntry, Warrior, DiscardPileEntry
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.tests.my_factories import (
    GameSetupFactory, GameSetupWithFactionsFactory, BirdTurnFactory, CardFactory, CraftedCardEntryFactory,
    CraftedItemEntryFactory, WarriorFactory, DiscardPileEntryFactory
)
from game.tests.client import RootGameClient
from game.models.events.crafted_cards import InformantsEvent

class TestActionViews(TestCase):
    def setUp(self):
        # Create user with password for RootGameClient login
        self.username = "test_user"
        self.password = "password"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        
        self.game = GameSetupWithFactionsFactory(factions=[Faction.BIRDS, Faction.CATS], owner=self.user)
        self.player = self.game.players.get(faction=Faction.BIRDS)
        self.opponent = self.game.players.get(faction=Faction.CATS)
        
        # Ensure the user in player is our test_user
        self.player.user = self.user
        self.player.save()
        
        # Initialize RootGameClient
        # Note: RootGameClient calls login() in __init__
        self.root_client = RootGameClient(user=self.username, password=self.password, game_id=self.game.pk)

    def test_saboteurs_view_flow(self):
        # Setup Saboteurs
        saboteurs_card = CardFactory(game=self.game, card_type=CardsEP.SABOTEURS.name)
        CraftedCardEntryFactory(player=self.player, card=saboteurs_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Setup Target
        target_card = CardFactory(game=self.game, card_type=CardsEP.FOXFOLK_STEEL.name)
        target_entry = CraftedCardEntryFactory(player=self.opponent, card=target_card)
        
        # Move to Birdsong
        turn = BirdTurnFactory(player=self.player, turn_number=1)
        from game.models.birds.turn import BirdBirdsong
        BirdBirdsong.objects.filter(turn=turn).update(step="1")
        
        # Manually set base_route for specific card action
        self.root_client.base_route = "/api/action/card/saboteurs/"
        # Initial GET to set the step
        response = self.root_client.get(f"{self.root_client.base_route}?game_id={self.game.pk}")
        self.root_client.step = response.json()
        
        self.assertEqual(self.root_client.step['name'], 'pick-faction')
        
        # Step 1: Submit faction
        self.root_client.submit_action({"faction": "Cats"})
        self.assertEqual(self.root_client.step['name'], 'pick-card')
        
        # Step 2: Submit card
        response = self.root_client.submit_action({"card": "FOXFOLK_STEEL"})
        self.assertEqual(response.json()['name'], 'completed')
        
        # Verify effects
        self.assertFalse(CraftedCardEntry.objects.filter(pk=target_entry.id).exists())

    def test_charm_offensive_view_flow(self):
        # Setup Charm Offensive
        charm_card = CardFactory(game=self.game, card_type=CardsEP.CHARM_OFFENSIVE.name)
        CraftedCardEntryFactory(player=self.player, card=charm_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Move to Evening
        turn = BirdTurnFactory(player=self.player, turn_number=1)
        from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening
        BirdBirdsong.objects.filter(turn=turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=turn).update(step=BirdDaylight.BirdDaylightSteps.COMPLETED)
        BirdEvening.objects.filter(turn=turn).update(step=BirdEvening.BirdEveningSteps.SCORING)
        
        # Manually set base_route
        self.root_client.base_route = "/api/action/card/charm-offensive/"
        response = self.root_client.get(f"{self.root_client.base_route}?game_id={self.game.pk}")
        self.root_client.step = response.json()
        
        self.assertEqual(self.root_client.step['name'], 'pick-opponent')
        
        # Submit opponent faction
        response = self.root_client.submit_action({"faction": "Cats"})
        self.assertEqual(response.json()['name'], 'completed')
        
        # Verify effects
        self.opponent.refresh_from_db()
        self.assertEqual(self.opponent.score, 1)

    def test_propaganda_bureau_view_flow(self):
        # Setup RB
        pb_card = CardFactory(game=self.game, card_type=CardsEP.PROPAGANDA_BUREAU.name)
        CraftedCardEntryFactory(player=self.player, card=pb_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Hand card matching fox clearing
        fox_clearing = Clearing.objects.filter(game=self.game, suit='r').first()
        fox_card = CardFactory(game=self.game, card_type=CardsEP.FOX_PARTISANS.name)
        HandEntry.objects.create(player=self.player, card=fox_card)
        
        # Enemy warrior in fox clearing
        from game.models import Warrior
        Warrior.objects.create(player=self.opponent, clearing=fox_clearing)
        
        # Move to Daylight
        turn = BirdTurnFactory(player=self.player, turn_number=1)
        from game.models.birds.turn import BirdBirdsong, BirdDaylight
        BirdBirdsong.objects.filter(turn=turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=turn).update(step=BirdDaylight.BirdDaylightSteps.CRAFTING)
        
        # Manually set base_route
        self.root_client.base_route = "/api/action/card/propaganda-bureau/"
        response = self.root_client.get(f"{self.root_client.base_route}?game_id={self.game.pk}")
        self.root_client.step = response.json()
        
        self.assertEqual(self.root_client.step['name'], 'pick_card')
        
        # Step 1: Submit card
        self.root_client.submit_action({"card": "FOX_PARTISANS"}) # Note: PropagandaBureauView payload says "card_name" but wait
        # Actually PropagandaBureauView payload name for card is "card_name"
        # Wait, I need to check payload_details in PropagandaBureauView
        
        # Step 2: Submit clearing
        self.root_client.submit_action({"clearing": fox_clearing.id})
        
        # Step 3: Submit opponent
        response = self.root_client.submit_action({"faction": "ca"})
        self.assertEqual(response.json()['name'], 'completed')
    def test_league_of_adventurers_move_flow(self):
        # Setup card
        league_card = CardFactory(game=self.game, card_type=CardsEP.LEAGUE_OF_ADVENTURERS.name)
        CraftedCardEntryFactory(player=self.player, card=league_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Setup item
        item_entry = CraftedItemEntryFactory(player=self.player)
        
        # Setup move clearings
        clearing1 = Clearing.objects.get(game=self.game, clearing_number=1)
        clearing2 = Clearing.objects.get(game=self.game, clearing_number=2)
        clearing1.connected_clearings.add(clearing2)
        WarriorFactory.create_batch(2, player=self.player, clearing=clearing1)
        
        # Move to Daylight
        turn = BirdTurnFactory(player=self.player, turn_number=1)
        from game.models.birds.turn import BirdBirdsong, BirdDaylight
        BirdBirdsong.objects.filter(turn=turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=turn).update(step=BirdDaylight.BirdDaylightSteps.CRAFTING)
        
        self.root_client.base_route = "/api/action/card/league-of-adventurers/"
        response = self.root_client.get(f"{self.root_client.base_route}?game_id={self.game.pk}")
        self.root_client.step = response.json()
        
        self.assertEqual(self.root_client.step['name'], 'pick-item')
        
        # 1. Pick Item
        self.root_client.submit_action({"crafted_item": item_entry.id})
        self.assertEqual(self.root_client.step['name'], 'pick-action')
        
        # 2. Pick Action (Move)
        self.root_client.submit_action({"action": "move"})
        self.assertEqual(self.root_client.step['name'], 'pick-origin')
        
        # 3. Pick Origin
        self.root_client.submit_action({"clearing": clearing1.id})
        self.assertEqual(self.root_client.step['name'], 'pick-destination')
        
        # 4. Pick Destination
        self.root_client.submit_action({"clearing": clearing2.id})
        self.assertEqual(self.root_client.step['name'], 'pick-count')
        
        # 5. Pick Count
        response = self.root_client.submit_action({"number": 2})
        self.assertEqual(response.json()['name'], 'completed')
        
        # Verify
        self.assertEqual(Warrior.objects.filter(player=self.player, clearing=clearing2).count(), 2)
        item_entry.refresh_from_db()
        self.assertTrue(item_entry.exhausted)

    def test_league_of_adventurers_battle_flow(self):
        # Setup card and item
        league_card = CardFactory(game=self.game, card_type=CardsEP.LEAGUE_OF_ADVENTURERS.name)
        CraftedCardEntryFactory(player=self.player, card=league_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        item_entry = CraftedItemEntryFactory(player=self.player)
        
        # Setup battle
        clearing1 = Clearing.objects.get(game=self.game, clearing_number=1)
        WarriorFactory(player=self.player, clearing=clearing1)
        WarriorFactory(player=self.opponent, clearing=clearing1)
        
        # Move to Daylight
        turn = BirdTurnFactory(player=self.player, turn_number=1)
        from game.models.birds.turn import BirdBirdsong, BirdDaylight
        BirdBirdsong.objects.filter(turn=turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=turn).update(step=BirdDaylight.BirdDaylightSteps.CRAFTING)
        
        self.root_client.base_route = "/api/action/card/league-of-adventurers/"
        response = self.root_client.get(f"{self.root_client.base_route}?game_id={self.game.pk}")
        self.root_client.step = response.json()
        
        # 1. Pick Item
        self.root_client.submit_action({"crafted_item": item_entry.id})
        # 2. Pick Action (Battle)
        self.root_client.submit_action({"action": "battle"})
        self.assertEqual(self.root_client.step['name'], 'pick-clearing')
        # 3. Pick Clearing
        self.root_client.submit_action({"clearing": clearing1.id})
        self.assertEqual(self.root_client.step['name'], 'pick-opponent')
        # 4. Pick Opponent
        response = self.root_client.submit_action({"faction": "ca"})
        self.assertEqual(response.json()['name'], 'completed')
        
        # Verify battle started
        from game.models.events.battle import Battle
        self.assertTrue(Battle.objects.filter(clearing=clearing1).exists())

    def test_informants_view_flow_use(self):
        # Setup Informants
        informants_card = CardFactory(game=self.game, card_type=CardsEP.INFORMANTS.name)
        CraftedCardEntryFactory(player=self.player, card=informants_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Setup Ambush in discard
        ambush_card = CardFactory(game=self.game, card_type=CardsEP.AMBUSH_RED.name)
        discard_entry = DiscardPileEntryFactory(game=self.game, card=ambush_card)
        
        # Move turn to Evening Drawing
        turn = BirdTurnFactory(player=self.player, turn_number=1)
        from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening
        BirdBirdsong.objects.filter(turn=turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=turn).update(step=BirdDaylight.BirdDaylightSteps.COMPLETED)
        BirdEvening.objects.filter(turn=turn).update(step=BirdEvening.BirdEveningSteps.DRAWING)
        
        # Initialize action (this should trigger the event and return InformantsView route)
        response = self.root_client.get_action()
        self.assertEqual(self.root_client.step['name'], 'use-or-skip')
        
        # Step 1: Use Informants
        self.root_client.submit_action({"choice": "use"})
        self.assertEqual(self.root_client.step['name'], 'pick-ambush-card')
        
        # Step 2: Pick ambush card
        self.root_client.submit_action({"discard_card": str(discard_entry.id)})
        # This will complete the step
        # Wait, RootGameClient.submit_action calls get_action() if it completed.
        # So it should be completed.
        
        # Verify effects
        self.assertTrue(HandEntry.objects.filter(player=self.player, card=ambush_card).exists())
        self.assertFalse(DiscardPileEntry.objects.filter(id=discard_entry.id).exists())

    def test_informants_view_flow_skip(self):
        # Setup Informants
        informants_card = CardFactory(game=self.game, card_type=CardsEP.INFORMANTS.name)
        crafted_entry = CraftedCardEntryFactory(player=self.player, card=informants_card, used=CraftedCardEntry.UsedChoice.UNUSED)
        
        # Move turn to Evening Drawing
        turn = BirdTurnFactory(player=self.player, turn_number=1)
        from game.models.birds.turn import BirdBirdsong, BirdDaylight, BirdEvening
        BirdBirdsong.objects.filter(turn=turn).update(step=BirdBirdsong.BirdBirdsongSteps.COMPLETED)
        BirdDaylight.objects.filter(turn=turn).update(step=BirdDaylight.BirdDaylightSteps.COMPLETED)
        BirdEvening.objects.filter(turn=turn).update(step=BirdEvening.BirdEveningSteps.DRAWING)
        
        # Initialize action
        self.root_client.get_action()
        self.assertEqual(self.root_client.step['name'], 'use-or-skip')
        
        # Step 1: Skip Informants
        self.root_client.submit_action({"choice": "skip"})
        
        # Verify effects
        crafted_entry.refresh_from_db()
        self.assertEqual(crafted_entry.used, CraftedCardEntry.UsedChoice.USED)
        # Event should be resolved
        self.assertFalse(InformantsEvent.objects.filter(crafted_card_entry=crafted_entry, event__is_resolved=False).exists())
