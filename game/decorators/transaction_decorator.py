import functools
import threading
from django.db import transaction
from game.models.game_models import Game
from game.models.checkpoint_models import Checkpoint, Action
from game.serializers.action_serializer import ActionSerializer
from game.utils.snapshot import capture_gamestate

# Context for playback to avoid infinite recursion
_playback_context = threading.local()

def set_playback_mode(enabled: bool):
    _playback_context.is_replaying = enabled

def is_playback_mode():
    return getattr(_playback_context, 'is_replaying', False)

def atomic_game_action(func, undoable : bool = True):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # return func(*args, **kwargs)
        if is_playback_mode():
            return func(*args, **kwargs)

        # Attempt to resolve the Game object from arguments
        game = None
        
        # Direct Game instance in args
        for arg in args:
            if isinstance(arg, Game):
                game = arg
                break
        
        # Check for object with 'game' attribute (e.g. Player or View)
        if not game and args:
             obj = args[0]
             if hasattr(obj, 'game'):
                 attr = getattr(obj, 'game')
                 
                 # obj.game is the Game instance (e.g. Player.game)
                 if isinstance(attr, Game):
                     game = attr
                 
                 # obj.game is a method (e.g. GameActionView.game(game_id))
                 elif callable(attr):
                     game_id = kwargs.get('game_id')
                     if game_id is None:
                         # Try to find game_id in positional args
                         for a in args[1:]:
                             if isinstance(a, int):
                                 game_id = a
                                 break
                     
                     if game_id is not None:
                         try:
                             game = attr(game_id)
                         except Exception:
                             pass
        
        if not game:
            # Fallback: execute without logging if game cannot be found
            return func(*args, **kwargs)

        with transaction.atomic():
            # Get the last checkpoint for the game
            last_checkpoint = Checkpoint.objects.filter(game=game).order_by('id').last()
            
            checkpoint = None
            if last_checkpoint:
                # Check if the serialized state matches the current turn
                # Find Game object in snapshot list
                snapshot_turn = None
                for obj in last_checkpoint.gamestate:
                    if obj['model'] == 'game.game':
                        snapshot_turn = obj['fields'].get('current_turn')
                        break
                
                if snapshot_turn == game.current_turn:
                    checkpoint = last_checkpoint

            if not checkpoint:
                # Create a new checkpoint
                gamestate_data = capture_gamestate(game)
                
                # Debug: Check DecreeEntry integrity
                for obj in gamestate_data:
                    if obj['model'] == 'game.decreeentry':
                        if 'column' not in obj['fields'] or obj['fields']['column'] is None:
                            print(f"CRITICAL: Caught bad DecreeEntry in snapshot: {obj}")

                checkpoint = Checkpoint.objects.create(
                    game=game,
                    gamestate=gamestate_data
                )

            # Serialize arguments for the action
            s_args, s_kwargs = ActionSerializer.serialize_args(args, kwargs)

            # Determine the order of this action within the checkpoint
            action_number = Action.objects.filter(checkpoint=checkpoint).count()

            # Record the action
            full_name = f"{func.__module__}.{func.__qualname__}"
            Action.objects.create(
                checkpoint=checkpoint,
                action_number=action_number,
                transaction_name=full_name,
                args={'args': s_args, 'kwargs': s_kwargs}
            )
            #execute function
            result = func(*args, **kwargs)
            if not undoable:
                # Create a new checkpoint
                gamestate_data = capture_gamestate(game)
                
                # Debug: Check DecreeEntry integrity
                for obj in gamestate_data:
                    if obj['model'] == 'game.decreeentry':
                        if 'column' not in obj['fields'] or obj['fields']['column'] is None:
                            print(f"CRITICAL: Caught bad DecreeEntry in snapshot: {obj}")

                checkpoint = Checkpoint.objects.create(
                    game=game,
                    gamestate=gamestate_data
                )
            return result

    return wrapper
