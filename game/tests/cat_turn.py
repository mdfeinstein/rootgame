from django.test import TestCase
from .client import RootGameClient
from django.core.management import call_command


class CatTurnTestCase(TestCase):
    fixtures = ["birds_finished_setup.json"]

    def setUp(self):
        self.cat_client = RootGameClient("user1", "password", 1)
        self.cat_client.login()
        self.cat_client.get_action()
        self.cat_client.print_responses = True
        hand = self.cat_client.get("/api/player-hand/")
        print(hand.json())

    def test_cats_turn_happy_path(self):
        """
        Test a simple turn 1 with cats
        """
        # BIRDSONG:
        # cats confirm wood placement
        self.cat_client.submit_action({"confirm": True})
        # DAYLIGHT:
        # cats craft: craft nothing
        self.cat_client.submit_action({"card": ""})
        # cats recruit
        self.cat_client.submit_action({"action_type": "recruit"})
        self.cat_client.submit_action({"confirm": True})
        # cats march
        self.cat_client.submit_action({"action_type": "march"})
        # move 1
        self.cat_client.submit_action({"clearing_number": 1})
        self.cat_client.submit_action({"clearing_number": 10})
        self.cat_client.submit_action({"number": 1})
        # move 2
        self.cat_client.submit_action({"clearing_number": 10})
        self.cat_client.submit_action({"clearing_number": 12})
        self.cat_client.submit_action({"number": 2})
        # cats build
        self.cat_client.submit_action({"action_type": "build"})
        self.cat_client.submit_action({"building_type": "workshop"})
        self.cat_client.submit_action({"clearing_number": 10})
        # end action step
        self.cat_client.submit_action({"action_type": ""})
        # confirm drawing
        self.cat_client.submit_action({"confirm": True})

        # save a fixture
        call_command(
            "dumpdata",
            "game",
            "auth.user",
            "--natural-foreign",
            "--indent=2",
            "--exclude=contenttypes",
            "--exclude=auth.permission",
            "--exclude=admin",
            "--exclude=sessions",
            output="game/fixtures/cats_finished_turn1.json",
        )
        pass
