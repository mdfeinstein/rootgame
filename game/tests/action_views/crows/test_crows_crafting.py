from rest_framework import status
from rest_framework.test import APITestCase
from game.models.game_models import Faction, Clearing, Card, HandEntry
from game.models.crows.tokens import PlotToken
from game.models.crows.turn import CrowTurn, CrowBirdsong
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.tests.client import RootGameClient
from game.tests.my_factories import GameSetupWithFactionsFactory

class CrowsCraftingTests(APITestCase):
    def setUp(self):
        self.game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.CROWS])
        self.crows_player = self.game.players.get(faction=Faction.CROWS)
        
        # Crows user
        self.crows_user = self.crows_player.user
        self.crows_user.set_password("p")
        self.crows_user.save()
        self.crows_client = RootGameClient(user=self.crows_user, password="p", game_id=self.game.id)
        
        # Fox clearings (RED): 1, 6
        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c6 = Clearing.objects.get(game=self.game, clearing_number=6)
        
        # Set turn to Crows
        self.game.current_turn = self.crows_player.turn_order
        self.game.save()
        
        # Enforce turn object existence
        self.turn = CrowTurn.objects.filter(player=self.crows_player).last()
        if not self.turn:
            self.turn = CrowTurn.create_turn(self.crows_player)
        self.birdsong = self.turn.birdsong.first()
        self.birdsong.step = CrowBirdsong.CrowBirdsongSteps.CRAFT
        self.birdsong.save()

    def test_crows_crafting_mixed_tokens(self):
        """Test crafting with one face-down and one face-up plot token."""
        # 1. Setup card in hand: FOXFOLK_STEEL (cost: 2 RED)
        card_enum = CardsEP.FOXFOLK_STEEL
        card_obj = Card.objects.filter(card_type=card_enum.name).first()
        HandEntry.objects.create(player=self.crows_player, card=card_obj)
        
        # 2. Setup tokens: one face-down in C1 (RED), one face-up in C6 (RED)
        PlotToken.objects.filter(player=self.crows_player).update(clearing=None) # Clear reserve
        
        p1 = PlotToken.objects.filter(player=self.crows_player, clearing__isnull=True).first()
        p1.clearing = self.c1
        p1.is_facedown = True
        p1.save()
        
        p2 = PlotToken.objects.filter(player=self.crows_player, clearing__isnull=True).exclude(id=p1.id).first()
        p2.clearing = self.c6
        p2.is_facedown = False
        p2.save()
        
        # 3. Get action
        self.crows_client.get_action()
        self.assertEqual(self.crows_client.step["name"], "select_card")
        
        # 4. Select card
        response = self.crows_client.submit_action({"card": card_enum.name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_pieces")
        
        # 5. Select first piece (face-down in C1)
        response = self.crows_client.submit_action({"clearing_number": self.c1.clearing_number})
        print(f"DEBUG: Piece post response: {response.status_code} {response.data if hasattr(response, 'data') else response.json()}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "select_pieces")
        
        # 6. Select second piece (face-up in C6)
        response = self.crows_client.submit_action({"clearing_number": self.c6.clearing_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "completed")
        
        # 7. Verify craft
        from game.models.game_models import CraftedItemEntry
        self.assertTrue(CraftedItemEntry.objects.filter(player=self.crows_player, item__item_type=card_enum.value.item.value).exists())
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertTrue(p1.crafted_with)
        self.assertTrue(p2.crafted_with)
