from django.test import TestCase
from game.models.game_models import Faction, Clearing, Warrior
from game.models.crows.turn import CrowTurn, CrowDaylight
from game.tests.my_factories import GameSetupFactory
from game.transactions.crows.daylight import do_daylight_action, end_daylight_action_step

class CrowDaylightTestCase(TestCase):
    def setUp(self):
        self.game = GameSetupFactory(factions=[Faction.CATS, Faction.CROWS])
        self.player = self.game.players.get(faction=Faction.CROWS)
        
        self.game.current_turn = self.player.turn_order
        self.game.save()
        
        self.turn = CrowTurn.create_turn(self.player)
        self.birdsong = self.turn.birdsong.first()
        self.birdsong.step = self.birdsong.CrowBirdsongSteps.COMPLETED
        self.birdsong.save()
        
        self.daylight = self.turn.daylight.first()
        self.daylight.step = CrowDaylight.CrowDaylightSteps.ACTIONS
        self.daylight.save()

        self.c1 = Clearing.objects.get(game=self.game, clearing_number=1)
        self.c2 = Clearing.objects.get(game=self.game, clearing_number=2)
        self.c1.connected_clearings.add(self.c2)
        self.c2.connected_clearings.add(self.c1)
        c1_ids = list(Warrior.objects.filter(player=self.player).values_list('id', flat=True)[:5])
        Warrior.objects.filter(id__in=c1_ids).update(clearing=self.c1)

    def test_do_daylight_action_decrements_actions(self):
        self.assertEqual(self.daylight.actions_remaining, 3)
        do_daylight_action(self.player, "move", origin=self.c1, destination=self.c2, count=1)
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.actions_remaining, 2)

    def test_do_daylight_action_fails_no_actions(self):
        self.daylight.actions_remaining = 0
        self.daylight.save()
        with self.assertRaisesMessage(ValueError, "No actions remaining"):
            do_daylight_action(self.player, "move", origin=self.c1, destination=self.c2, count=1)

    def test_end_daylight_action_step(self):
        end_daylight_action_step(self.player)
        self.daylight.refresh_from_db()
        self.assertEqual(self.daylight.step, CrowDaylight.CrowDaylightSteps.COMPLETED)
        evening = self.turn.evening.first()
        self.assertEqual(evening.step, evening.CrowEveningSteps.EXERT)
