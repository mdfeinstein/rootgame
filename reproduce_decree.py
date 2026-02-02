import django
import os
import sys

# Setup Django environment
sys.path.append('f:/rootGame')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rootGame.settings')
django.setup()

from game.models.game_models import Game, Player, Faction, Card
from game.models.birds.player import DecreeEntry
from game.utils.snapshot import capture_gamestate
from game.utils.loader import load_gamestate
from django.db import transaction

@transaction.atomic
def run_test():
    # 1. Setup
    print("Setting up game...")
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(username='testuser')
    Game.objects.filter(id=9998).delete()
    game = Game.objects.create(id=9998, owner=user)
    player = Player.objects.create(game=game, user=user, faction=Faction.BIRDS, turn_order=1)
    
    # Create a dummy card
    card = Card.objects.create(game=game, suit='r', card_type='FOX_PARTISANS')
    
    # Create Decree Entry
    decree = DecreeEntry.objects.create(
        player=player, 
        card=card, 
        column=DecreeEntry.Column.RECRUIT
    )
    print(f"Created Decree Entry: {decree.column} (Card: {decree.card})")

    from game.models.birds.player import Vizier, BirdLeader
    # Create Leader (needed for Vizier creation utility, but we can create manually)
    BirdLeader.objects.create(player=player, leader=BirdLeader.BirdLeaders.CHARISMATIC, active=True)
    Vizier.create_viziers(player)
    print(f"Created Viziers. Count: {Vizier.objects.filter(player=player).count()}")
    
    # 2. Capture Snapshot
    print("Capturing Snapshot...")
    gamestate_data = capture_gamestate(game)
    
    # Verify Snapshot Data
    found_decree = False
    for obj in gamestate_data:
        if obj['model'] == 'game.decreeentry':
            fields = obj['fields']
            print(f"Snapshot Decree Fields: {fields}")
            if 'column' not in fields or fields['column'] is None:
                print("ERROR: 'column' field missing or None in snapshot!")
            else:
                found_decree = True
                
    if not found_decree:
        print("ERROR: DecreeEntry not found in snapshot!")
        
    # 3. Restore
    print("Restoring...")
    # Clean DB to force creation
    DecreeEntry.objects.filter(player=player).delete()
    
    try:
        load_gamestate(9998, gamestate_data)
        print("Restore successful.")
    except Exception as e:
        print(f"Restore FAILED: {e}")
        # raise # re-raise to see traceback if needed

    # Verify
    if DecreeEntry.objects.filter(player=player).exists():
        d = DecreeEntry.objects.get(player=player)
        print(f"Restored Decree: {d.column}")
    else:
        print("DecreeEntry not restored.")

    raise Exception("Rolling back")

try:
    run_test()
except Exception as e:
    print(e)
