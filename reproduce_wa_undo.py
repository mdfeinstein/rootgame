import django
import os
import sys

# Setup Django environment
sys.path.append('f:/rootGame')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rootGame.settings')
django.setup()

from game.models.game_models import Game, Player, Faction, Clearing
from game.models.wa.tokens import WASympathy
from game.utils.snapshot import capture_gamestate
from game.utils.loader import load_gamestate
from django.db import transaction

@transaction.atomic
def run_test():
    # 1. Setup
    print("Setting up game...")
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(username='testuser')
    Game.objects.filter(id=9997).delete()
    game = Game.objects.create(id=9997, owner=user)
    # Create WA Player
    player = Player.objects.create(game=game, user=user, faction=Faction.WOODLAND_ALLIANCE, turn_order=1)
    
    # Clearing for sympathy
    clearing = Clearing.objects.create(game=game, clearing_number=1, suit='r')
    
    # 2. Capture Snapshot (Before placing sympathy)
    print("Capturing Snapshot...")
    gamestate_data = capture_gamestate(game)
    
    # 3. Perform Action: Create WASympathy
    print("Placing Sympathy...")
    sympathy = WASympathy.objects.create(player=player, clearing=clearing)
    print(f"Sympathy Created: {sympathy} (ID: {sympathy.id})")
    print(f"Total Sympathy Count: {WASympathy.objects.filter(player=player).count()}")
    
    # 4. Restore (Undo)
    print("Restoring...")
    load_gamestate(9997, gamestate_data)
    
    # 5. Verify Culling
    count = WASympathy.objects.filter(player=player).count()
    print(f"Total Sympathy Count after restore: {count} (Expected 0)")
    
    if count == 0:
        print("SUCCESS: Sympathy token culled.")
    else:
        print("FAILURE: Sympathy token persists.")
        remaining = WASympathy.objects.filter(player=player)
        for t in remaining:
            print(f"  Remaining: {t} (ID: {t.id})")

    raise Exception("Rolling back")

try:
    run_test()
except Exception as e:
    print(e)
