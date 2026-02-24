from unittest.mock import patch
from rest_framework import status
from game.models.events.battle import Battle
from game.models.game_models import Faction, Player, Clearing
from game.tests.client import RootGameClient
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, WarriorFactory
from game.transactions.battle import start_battle, defender_ambush_choice
from game.game_data.cards.exiles_and_partisans import CardsEP
from rest_framework.test import APITestCase

class BattleActionViewTests(APITestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(
            factions=[Faction.CATS, Faction.BIRDS]
        )
        self.cats = Player.objects.get(game=self.game, faction=Faction.CATS)
        self.birds = Player.objects.get(game=self.game, faction=Faction.BIRDS)
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        
        self.cats.user.set_password("password")
        self.cats.user.save()
        self.birds.user.set_password("password")
        self.birds.user.save()
        
        self.client_cats = RootGameClient(self.cats.user.username, "password", self.game.id)
        self.client_birds = RootGameClient(self.birds.user.username, "password", self.game.id)
        
        # Clear out existing pieces from setup to ensure controlled conditions
        from game.models.game_models import Warrior, Building, Token
        Warrior.objects.filter(clearing=self.c1).delete()
        Building.objects.filter(building_slot__clearing=self.c1).delete()
        Token.objects.filter(clearing=self.c1).delete()

    def _setup_battle_and_get_event(self):
        start_battle(self.game, Faction.CATS, Faction.BIRDS, self.c1)
        
        # force the current action to point to the battle
        self.game.current_turn = self.cats.turn_order
        self.game.active_player_order = self.cats.turn_order
        self.game.save()
        
        return Battle.objects.get(clearing=self.c1)

    @patch('game.transactions.battle.randint')
    def test_battle_flow_no_ambushes(self, mock_randint):
        mock_randint.side_effect = [2, 0]  
        WarriorFactory.create_batch(3, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(1, player=self.birds, clearing=self.c1)
        
        from game.models.birds.buildings import BirdRoost
        from game.models.game_models import BuildingSlot
        s1 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=1)
        s2 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=2)
        BirdRoost.objects.create(player=self.birds, building_slot=s1)
        BirdRoost.objects.create(player=self.birds, building_slot=s2)
        
        battle = self._setup_battle_and_get_event()

        # STEP 1: Defender Ambush Check
        self.client_birds.get_action()
        self.assertEqual(self.client_birds.step["name"], "ambush-check-defender")
        
        # Defender chooses not to ambush.
        response = self.client_birds.post_action({"ambush_card": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.DEFENDER_CHOOSE_HITS.value)
        
        # STEP 2: Defender Choose Hits
        self.client_birds.get_action()
        self.assertEqual(self.client_birds.step["name"], "choose-hit-defender")
        
        options = self.client_birds.step["options"]
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0]["value"], "BirdRoost")
        
        # POST choice
        response = self.client_birds.post_action({"piece": "BirdRoost"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED.value)

    @patch('game.transactions.battle.randint')
    def test_attacker_choose_ambush_flow(self, mock_randint):
        mock_randint.side_effect = [1, 1]
        WarriorFactory.create_batch(1, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(3, player=self.birds, clearing=self.c1)
        
        from game.models.game_models import Card, HandEntry
        card = Card.objects.filter(game=self.game, card_type=CardsEP.AMBUSH_RED.name).first()
        HandEntry.objects.create(player=self.birds, card=card)
        
        from game.models.cats.buildings import Sawmill
        from game.models.game_models import BuildingSlot
        s1 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=1)
        Sawmill.objects.create(player=self.cats, building_slot=s1)
        
        battle = self._setup_battle_and_get_event()
        
        # Defender Ambush
        self.client_birds.get_action()
        response = self.client_birds.post_action({"ambush_card": "AMBUSH_RED"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.ATTACKER_AMBUSH_CANCEL_CHECK.value)
        
        # Attacker takes ambush, loses 1 warrior, must choose ambush hit
        self.client_cats.get_action()
        response = self.client_cats.post_action({"ambush_card": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.ATTACKER_CHOOSE_AMBUSH_HITS.value)
        
        # Attacker Chooses Ambush Hit
        self.client_cats.get_action()
        self.assertEqual(self.client_cats.step["name"], "choose-ambush-hit-attacker")
        self.assertEqual(self.client_cats.step["options"][0]["value"], "Sawmill")
        
        response = self.client_cats.post_action({"piece": "Sawmill"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED.value)

    @patch('game.transactions.battle.randint')
    def test_attacker_choose_hits_after_battle_flow(self, mock_randint):
        mock_randint.side_effect = [3, 3]  
        WarriorFactory.create_batch(1, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(2, player=self.birds, clearing=self.c1)
        
        from game.models.cats.buildings import Sawmill, Recruiter
        from game.models.game_models import BuildingSlot
        s1 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=1)
        s2 = BuildingSlot.objects.create(clearing=self.c1, building_slot_number=2)
        Sawmill.objects.create(player=self.cats, building_slot=s1)
        Recruiter.objects.create(player=self.cats, building_slot=s2)
        
        battle = self._setup_battle_and_get_event()
        defender_ambush_choice(self.game, battle, None) # skip straight to roll dice and assigning
        
        # Takes hits, min(1, 3) = 1. Takes 1 warrior. 1 Hit left, but Sawmill and Recruiter exist
        # Attacker should choose
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.ATTACKER_CHOOSE_HITS.value)
        
        self.client_cats.get_action()
        self.assertEqual(self.client_cats.step["name"], "choose-hit-attacker")
        self.assertEqual(len(self.client_cats.step["options"]), 2)
        
        response = self.client_cats.post_action({"piece": "Sawmill"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        battle.refresh_from_db()
        self.assertEqual(battle.step, Battle.BattleSteps.COMPLETED.value)

    def test_invalid_validations(self):
        WarriorFactory.create_batch(1, player=self.cats, clearing=self.c1)
        WarriorFactory.create_batch(1, player=self.birds, clearing=self.c1)
        battle = self._setup_battle_and_get_event()
        
        # Wrong player tries to ambush
        self.client_cats.get_action() # actually cats gets the wrong action here if game is stuck on battle! 
        # Well, get_action doesn't validate user at GET normally, wait it does...
        # For Battle, player validation only happens on POST via dynamically assigned self.faction 
        # But wait, RootGameClient get_action reads from /api/game/current-action/1/
        
        # Let's hit the endpoint manually to assert validation exceptions
        base_route = "/api/battle/"
        # Fake it since RootGameClient is strict
        self.client_cats.step = {"endpoint": "ambush-check-defender"}
        self.client_cats.base_route = base_route
        response = self.client_cats.post_action({"ambush_card": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0], "Player is not the correct faction for this action")
