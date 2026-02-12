import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rootGame.settings")
django.setup()

import pytest
from django.db import models
from game.models.game_models import Game
from game.decorators.transaction_decorator import atomic_game_action
from channels.testing import WebsocketCommunicator
from game.consumers import GameConsumer
from channels.routing import URLRouter
from django.urls import re_path
from asgiref.sync import sync_to_async


# Mock function decorated with atomic_game_action
@atomic_game_action
def mock_game_action(game):
    return "Action Executed"


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_transaction_decorator_publishes_message():
    # Create a user
    from django.contrib.auth.models import User

    user = await sync_to_async(User.objects.create)(username="testuser")

    # Create a game
    # We need to run this in sync context
    game = await sync_to_async(Game.objects.create)(id=999, owner=user)

    # Setup WebSocket communicator
    application = URLRouter(
        [
            re_path(r"ws/game/(?P<game_id>\w+)/$", GameConsumer.as_asgi()),
        ]
    )
    communicator = WebsocketCommunicator(application, f"/ws/game/{game.id}/")
    connected, subprotocol = await communicator.connect()
    assert connected

    # Authenticate
    from rest_framework_simplejwt.tokens import AccessToken

    token = AccessToken.for_user(user)
    await communicator.send_json_to({"type": "authenticate", "token": str(token)})
    auth_response = await communicator.receive_json_from()
    assert auth_response == {"type": "authenticated"}

    # Execute the decorated function
    # atomic_game_action wraps the function, so calling it should trigger the publish
    # We need to run this in a way that allows the async signal to be sent?
    # atomic_game_action is synchronous. channels_redis uses async_to_sync.
    # It should work.

    await sync_to_async(mock_game_action)(game)

    # Check if message is received
    response = await communicator.receive_json_from(timeout=2)
    assert response == {"message": "update"}

    await communicator.disconnect()
