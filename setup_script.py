#!/usr/bin/env python
import os
import django

# 1. point to your settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rootGame.settings")

# 2. initialize Django
django.setup()

# 3. import your models

from game.models.cats.buildings import CatBuildingTypes
from game.models import (
    BuildingSlot,
    Clearing,
    Faction,
    FactionChoiceEntry,
    Game,
)
from django.contrib.auth.models import User
from game.transactions.game_setup import (
    assign_turn_order,
    autumn_map_setup,
    construct_deck,
    create_craftable_item_supply,
    create_new_game,
    add_new_player_to_game,
    player_picks_faction,
)
from game.transactions.cats_setup import (
    create_cats_buildings,
    create_cats_warrior_supply,
    create_cats_wood_supply,
    pick_corner as cats_pick_corner,
    place_garrison,
    place_initial_building,
    start_simple_cats_setup,
    confirm_completed_setup as cats_confirm_completed_setup,
)

from game.models.birds.player import BirdLeader
from game.transactions.birds_setup import (
    choose_leader_initial,
    create_bird_leaders,
    create_birds_buildings,
    create_birds_warrior_supply,
    start_simple_birds_setup,
    pick_corner as birds_pick_corner,
    confirm_completed_setup as birds_confirm_completed_setup,
)
from game.transactions.wa_setup import wa_setup
from game.transactions.general import draw_card_from_deck
from django.db import transaction


@transaction.atomic
def main():
    # create three users
    user1 = User.objects.create_user(username="user1", password="password")
    user2 = User.objects.create_user(username="user2", password="password")
    user3 = User.objects.create_user(username="user3", password="password")
    # user1 = User.objects.get(username="user1")
    # user2 = User.objects.get(username="user2")
    # user3 = User.objects.get(username="user3")
    # create game
    game = create_new_game(
        owner=User.objects.get(username="user1"), map=Game.BoardMaps.AUTUMN
    )
    # add players to game
    player1 = add_new_player_to_game(game, user1)
    player2 = add_new_player_to_game(game, user2)
    player3 = add_new_player_to_game(game, user3)

    # pick factions
    player_picks_faction(
        player=player1, faction=FactionChoiceEntry(game=game, faction=Faction.CATS)
    )
    player_picks_faction(
        player=player2, faction=FactionChoiceEntry(game=game, faction=Faction.BIRDS)
    )
    player_picks_faction(
        player=player3,
        faction=FactionChoiceEntry(game=game, faction=Faction.WOODLAND_ALLIANCE),
    )

    # setup general game
    assign_turn_order(game)
    create_craftable_item_supply(game)
    autumn_map_setup(game)
    construct_deck(game)
    # setup cats
    start_simple_cats_setup(player1)
    corner = Clearing.objects.get(game=game, clearing_number=1)
    cats_pick_corner(player1, corner)
    opposite_corner = Clearing.objects.get(game=game, clearing_number=3)
    place_garrison(player1, opposite_corner)
    ### get clearings 1, 9, 5
    clearing1 = Clearing.objects.get(game=game, clearing_number=1)
    clearing2 = Clearing.objects.get(game=game, clearing_number=9)
    clearing3 = Clearing.objects.get(game=game, clearing_number=5)
    place_initial_building(player1, clearing1, CatBuildingTypes.WORKSHOP)
    place_initial_building(player1, clearing2, CatBuildingTypes.SAWMILL)
    place_initial_building(player1, clearing3, CatBuildingTypes.RECRUITER)
    cats_confirm_completed_setup(player1)

    # setup birds
    start_simple_birds_setup(player2)
    birds_pick_corner(player2, opposite_corner)
    choose_leader_initial(player2, BirdLeader.BirdLeaders.DESPOT)
    birds_confirm_completed_setup(player2)

    # setup wa
    wa_setup(player3)
    # players draw three cards each from deck
    for i in range(3):
        draw_card_from_deck(player1)
        draw_card_from_deck(player2)
        draw_card_from_deck(player3)


if __name__ == "__main__":
    main()
