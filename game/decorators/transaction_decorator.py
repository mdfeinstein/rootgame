import functools
import threading
from django.db import transaction
from game.models.game_models import Game
from game.models.checkpoint_models import Checkpoint, Action
from game.serializers.game_state_serializer import GameStateSerializer
from game.serializers.action_serializer import ActionSerializer

# Context for playback to avoid infinite recursion
_playback_context = threading.local()

def set_playback_mode(enabled: bool):
    _playback_context.is_replaying = enabled

def is_playback_mode():
    return getattr(_playback_context, 'is_replaying', False)

def atomic_game_action(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
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
            # Get or create the checkpoint for the current turn
            checkpoint, created = Checkpoint.objects.get_or_create(
                game=game,
                turn_number=game.current_turn,
                defaults={
                    'gamestate': {} 
                }
            )
            
            if created:
                # Serialize state at the start of the checkpoint
                serializer = GameStateSerializer(game)
                checkpoint.gamestate = serializer.data
                checkpoint.save()

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

            return func(*args, **kwargs)

    return wrapper
