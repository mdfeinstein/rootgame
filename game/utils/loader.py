from django.core import serializers
from django.db import transaction
from game.utils.snapshot import get_all_game_objects
from game.models.game_models import Game

@transaction.atomic
def load_gamestate(game_id: int, gamestate_data: list):
    """
    Restores the game state from a snapshot (list of dicts).
    1. Deserializes the snapshot.
    2. Culls (deletes) any current game objects that are NOT in the snapshot.
    3. Saves (updates/creates) objects from the snapshot.
    """
    # 1. Deserialize
    # deserialized_objects is a generator of DeserializedObject wrappers
    # We use 'python' format because gamestate_data is already a python list (from JSONField)
    print(gamestate_data)
    deserialized_objects = list(serializers.deserialize('python', gamestate_data))
    
    # Map of (Model, PK) -> DeserializedObject
    snapshot_map = {
        (obj.object.__class__, obj.object.pk): obj 
        for obj in deserialized_objects
    }

    # 2. Cull
    try:
        current_game = Game.objects.get(pk=game_id)
        current_objects = get_all_game_objects(current_game)
        
        # Determine what to delete
        # Iterate in REVERSE of collection order (leaves first) to respect FK dependencies during deletion
        for obj in reversed(current_objects):
            # Key identification: (Model Class, PK)
            # Note: For MTI, exact class match matters. 
            # get_all_game_objects returns leaf classes.
            key = (obj.__class__, obj.pk)
            
            # Special case for Game: Do not delete the Game object itself!
            if isinstance(obj, Game):
                continue
                
            if key not in snapshot_map:
                # This object exists in DB but not in snapshot. Delete it.
                obj.delete()
                
    except Game.DoesNotExist:
        pass

    # 3. Restore (Update/Create)
    # Iterate in original order (dependencies first: Game -> Player -> ...)
    for dobj in deserialized_objects:
        # dobj.save() saves to DB. 
        # It handles both update (if PK exists) and create (if not).
        try:
            dobj.save()
        except Exception as e:
            print(f"ERROR saving object: {dobj.object} (Type: {dobj.object.__class__.__name__})")
            if hasattr(dobj.object, '__dict__'):
                print(f"Object dict: {dobj.object.__dict__}")
            raise e

    # 4. (SQLite Specifc) Reset Sequences
    # Since we culled objects, we might have rolled back the 'tip' of the table.
    # SQLite does not auto-reset autoincrement sequences on delete, so next insert will use old_max + 1,
    # causing mismatches with recorded Actions that expect reused PKs.
    from django.db import connection, connections
    from django.db.models import Max
    
    if 'sqlite' in connection.vendor:
        # Identify all models we just touched
        restored_models = set(dobj.object.__class__ for dobj in deserialized_objects)
        
        with connection.cursor() as cursor:
            for model in restored_models:
                table_name = model._meta.db_table
                max_id = model.objects.all().aggregate(Max('id'))['id__max']
                if max_id is None:
                    max_id = 0
                
                # Update sqlite_sequence
                # Note: We blindly set it to max_id. 
                # If other games exist with higher IDs, max_id will reflect that, preventing reuse (which is correct behavior to avoid corruption).
                # If we are the only game, max_id will be the snapshot's max, allowing reuse of the next IDs.
                try:
                    cursor.execute("UPDATE sqlite_sequence SET seq = %s WHERE name = %s", [max_id, table_name])
                except Exception:
                    # Table might not depend on sequence or other error, safe to ignore usually
                    pass
