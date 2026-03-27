import os
import sys
import django

# Add the project root to sys.path
sys.path.append('f:/rootGame')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rootGame.settings")
django.setup()

from game.models import (
    Faction, Game, Player, Clearing, Suit, Warrior
)
from game.models.wa.buildings import WABase
from game.models.wa.player import SupporterStackEntry
from game.models.cats.buildings import Workshop
from game.tests.my_factories import GameSetupWithFactionsFactory, CardFactory, WarriorFactory
from game.transactions.wa import revolt, draw_cards
from game.models.game_log import GameLog, LogType
from django.contrib.auth.models import User

# Setup
from django.contrib.auth.models import User
User.objects.filter(username__startswith="user_").delete()
User.objects.filter(username="debug_user_wa").delete()
user = User.objects.create(username="debug_user_wa")
# Clear previous data to avoid conflicts if possible, or just create a new game
game = GameSetupWithFactionsFactory(factions=[Faction.CATS, Faction.WOODLAND_ALLIANCE], owner=user)
wa_player = game.players.get(faction=Faction.WOODLAND_ALLIANCE)
cats_player = game.players.get(faction=Faction.CATS)

# 1. Test Revolt Logs
# Just pick any Mouse clearing
clearing = Clearing.objects.filter(game=game, suit=Suit.ORANGE).first()
if not clearing:
    # If no orange clearing, just pick any
    clearing = Clearing.objects.filter(game=game).first()
# Clear clearing
Warrior.objects.filter(clearing=clearing).delete()
# Add 1 warrior and 1 workshop
WarriorFactory(player=cats_player, clearing=clearing)
from game.queries.general import available_building_slot
slot = available_building_slot(clearing)
Workshop.objects.create(player=cats_player, building_slot=slot)

# Add supporters
for _ in range(2):
    card = CardFactory(game=game, suit=Suit.ORANGE)
    SupporterStackEntry.objects.create(player=wa_player, card=card)

# Place sympathy
from game.models.wa.tokens import WASympathy
token = WASympathy.objects.filter(player=wa_player, clearing=None).first()
token.clearing = clearing
token.save()

print("Before Revolt...")
revolt(wa_player, clearing)
print("After Revolt.")

log = GameLog.objects.filter(log_type=LogType.WA_REVOLT).last()
print(f"Revolt Log Details: {log.details}")

# 2. Test Draw Logs
from game.transactions.general import create_turn
from game.models.wa.turn import WATurn, WAEvening
turn = WATurn.create_turn(wa_player)
evening = turn.evening.first()
evening.step = WAEvening.WAEveningSteps.DRAWING
evening.save()

print("Before Draw...")
draw_cards(wa_player)
print("After Draw.")

draw_log = GameLog.objects.filter(log_type=LogType.DRAW).last()
if draw_log:
    print(f"Draw Log Details: {draw_log.details}")
else:
    print("No Draw Log found!")
