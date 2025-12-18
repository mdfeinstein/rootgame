from django.test import TestCase

from game.tests.client import RootGameClient
from django.core.management import call_command


class BirdTurnTestCase(TestCase):
    fixtures = ["cats_finished_turn1.json"]

    def setUp(self):
        self.bird_client = RootGameClient("user2", "password", 1)
        self.bird_client.login()
        self.print_responses = True
        self.bird_client.get_action()
        print(self.bird_client.last_get_response.json())
        hand = self.bird_client.get("/api/player-hand/")
        print(hand.json())
        """[
        {'card_name': 'ROOT_TEA_YELLOW', 'suit': 'y', 'suit_name': 'Rabbit', 'title': 'Root Tea', 'text': '', 'craftable': True, 'cost': ['Mouse'], 'item': '5', 'crafted_points': 2, 'ambush': False, 'dominance': False},
        {'card_name': 'DOMINANCE_ORANGE', 'suit': 'o', 'suit_name': 'Mouse', 'title': 'Dominance', 'text': '', 'craftable': False, 'cost': [], 'item': None, 'crafted_points': 0, 'ambush': False, 'dominance': True},
        {'card_name': 'DOMINANCE_WILD', 'suit': 'b', 'suit_name': 'Bird', 'title': 'Dominance', 'text': '', 'craftable': False, 'cost': [], 'item': None, 'crafted_points': 0, 'ambush': False, 'dominance': True}]
        """

    def test_bird_turn_happy_path(self):
        """
        Test a simple turn 1 with birds
        """
        # BIRDSONG:
        # confirm emergency draw step
        self.bird_client.submit_action({"confirm": True})
        # add to decree
        # yellow to recruit
        self.bird_client.submit_action({"card": "ROOT_TEA_YELLOW"})
        self.bird_client.submit_action({"decree_column": "RECRUIT"})
        # bird to battle
        self.bird_client.submit_action({"card": "DOMINANCE_WILD"})
        self.bird_client.submit_action({"decree_column": "BATTLE"})
        # emergency roosting step (automated, ignore)

        # DAYLIGHT:
        # craft: craft nothing
        self.bird_client.submit_action({"card": ""})
        # recruit
        self.bird_client.submit_action({"clearing_number": "3"})
        # move
        self.bird_client.submit_action({"clearing_number": "3"})  # origin
        self.bird_client.submit_action({"clearing_number": "7"})  # destination
        self.bird_client.submit_action({"number": 4})
        # battle
        self.bird_client.submit_action({"clearing_number": "7"})
        self.bird_client.submit_action({"faction": "CATS"})
        ## resolve battle: cats decline ambush
        cat_client = RootGameClient("user1", "password", 1)
        cat_client.login()
        cat_client.get_action()
        cat_client.submit_action({"card": ""})
        # save here, since evening not implemented yet (and build will move to evening)
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
            output="game/fixtures/birds_finished_turn1.json",
        )
        # build
        self.bird_client.get_action()  # need to get action again since cats did stuff
        self.bird_client.submit_action({"clearing_number": 7})

        # EVENING:
        # draw cards
