import importlib
from django.db import transaction
from game.models.game_models import Game
from game.models.checkpoint_models import Checkpoint, Action
from game.utils.loader import load_gamestate
from game.decorators.transaction_decorator import set_playback_mode
from game.serializers.action_serializer import ActionSerializer

def get_function_by_name(full_name):
    try:
        module_name, func_name = full_name.rsplit('.', 1)
        module = importlib.import_module(module_name)
        func = getattr(module, func_name)
        return func
    except (ValueError, ImportError, AttributeError):
        raise ValueError(f"Could not resolve function: {full_name}")

@transaction.atomic
def playback_to_action(game: Game, turn_number: int, action_number: int):
    # Find Checkpoint for the turn

    try:
        checkpoint = Checkpoint.objects.get(game=game, turn_number=turn_number)
    except Checkpoint.DoesNotExist:
        return 


    # Restore Game State from checkpoint

    load_gamestate(game.id, checkpoint.gamestate)
    
    # Reload game object
    game.refresh_from_db()

    # Retrieve actions to replay
    actions = Action.objects.filter(
        checkpoint=checkpoint, 
        action_number__lte=action_number
    ).order_by('action_number')

    # Replay actions

    set_playback_mode(True)
    try:
        for action in actions:
            func = get_function_by_name(action.transaction_name)
            
            # Deserialize args
            raw_args = action.args.get('args', [])
            raw_kwargs = action.args.get('kwargs', {})
            
            d_args, d_kwargs = ActionSerializer.deserialize_args(raw_args, raw_kwargs)
            
            # Execute
            func(*d_args, **d_kwargs)
            
    finally:
        set_playback_mode(False)

@transaction.atomic
def undo_last_action(game: Game):
    current_turn = game.current_turn
    checkpoint = Checkpoint.objects.filter(game=game, turn_number=current_turn).first()
    
    # helper to process undo on a specific checkpoint
    def undo_on_checkpoint(cp, turn):
        actions = Action.objects.filter(checkpoint=cp).order_by('action_number')
        if actions.exists():
            last_action = actions.last()
            last_action.delete()
            # Playback to the NEW last action (if any)
            new_last_index = actions.count() - 1 # count() is fresh after delete
            playback_to_action(game, turn, new_last_index)
            return True
        return False

    # Try to undo on current turn first
    if checkpoint:
        if undo_on_checkpoint(checkpoint, current_turn):
            return
        # If checkpoint exists but empty, delete it and fall through to prev turn
        checkpoint.delete()

    # Try previous turn if current turn had no actions to undo

    target_turn = current_turn - 1
    prev_cp = Checkpoint.objects.filter(game=game, turn_number=target_turn).first()
    
    if prev_cp:
        # Undo the last action of the previous turn (which caused the turn switch)
        undo_on_checkpoint(prev_cp, target_turn)
        
        # If previous checkpoint is now empty, ensure state is loaded
        if not Action.objects.filter(checkpoint=prev_cp).exists():
             playback_to_action(game, target_turn, -1)
