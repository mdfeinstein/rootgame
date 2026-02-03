import importlib
from django.db import transaction
from game.models.game_models import Game
from game.models.checkpoint_models import Checkpoint, Action
from game.utils.loader import load_gamestate
from game.decorators.transaction_decorator import set_playback_mode
from game.serializers.action_serializer import ActionSerializer


def get_function_by_name(full_name):
    try:
        module_name, func_name = full_name.rsplit(".", 1)
        module = importlib.import_module(module_name)
        func = getattr(module, func_name)
        return func
    except (ValueError, ImportError, AttributeError):
        raise ValueError(f"Could not resolve function: {full_name}")


@transaction.atomic
def playback_to_action(game: Game, checkpoint_id: int, action_number: int):
    # Find Checkpoint
    try:
        checkpoint = Checkpoint.objects.get(id=checkpoint_id, game=game)
    except Checkpoint.DoesNotExist:
        return

    # Restore Game State from checkpoint

    load_gamestate(game.id, checkpoint.gamestate)

    # Reload game object
    game.refresh_from_db()

    # Retrieve actions to replay
    actions = Action.objects.filter(
        checkpoint=checkpoint, action_number__lte=action_number
    ).order_by("action_number")

    # Replay actions

    set_playback_mode(True)
    try:
        for action in actions:
            print(f"Action: {action.transaction_name}")
            func = get_function_by_name(action.transaction_name)
            print(f"func: {func}")
            # Deserialize args
            raw_args = action.args.get("args", [])
            raw_kwargs = action.args.get("kwargs", {})
            print(f"raw_args: {raw_args}")
            print(f"raw_kwargs: {raw_kwargs}")
            d_args, d_kwargs = ActionSerializer.deserialize_args(raw_args, raw_kwargs)
            print(f"Args: {d_args}, {d_kwargs}")

            # Execute
            func(*d_args, **d_kwargs)

    finally:
        set_playback_mode(False)


@transaction.atomic
@transaction.atomic
def undo_last_action(game: Game):
    # Get the MOST RECENT checkpoint
    checkpoint = Checkpoint.objects.filter(game=game).order_by("id").last()

    if not checkpoint:
        return

    actions = Action.objects.filter(checkpoint=checkpoint).order_by("action_number")
    if actions.exists():
        last_action = actions.last()
        last_action.delete()
        # Playback to the NEW last action (if any)
        # Note: If actions.count() was 1, it is now 0. new_last_index = -1.
        new_last_index = actions.count() - 1
        playback_to_action(game, checkpoint.id, new_last_index)
    else:
        # right now, doesn't traverse to previous checkpoint if there are no actions
        pass
