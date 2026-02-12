import os
import django
import pytest
from channels.testing import WebsocketCommunicator

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rootGame.settings")
django.setup()

from game.consumers import GameConsumer
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from django.urls import re_path
from asgiref.sync import sync_to_async


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_game_consumer():
    from django.contrib.auth.models import User
    from game.models.game_models import Game
    from rest_framework_simplejwt.tokens import AccessToken
    from asgiref.sync import sync_to_async

    user = await sync_to_async(User.objects.create)(username="test_ws_user")
    game = await sync_to_async(Game.objects.create)(id=123, owner=user)
    token = AccessToken.for_user(user)

    application = URLRouter(
        [
            re_path(r"ws/game/(?P<game_id>\w+)/$", GameConsumer.as_asgi()),
        ]
    )
    communicator = WebsocketCommunicator(application, "/ws/game/123/")
    connected, subprotocol = await communicator.connect()
    assert connected

    # Send authentication
    await communicator.send_json_to({"type": "authenticate", "token": str(token)})

    # Expect authenticated response
    response = await communicator.receive_json_from()
    assert response == {"type": "authenticated"}

    # Simulate game update
    await communicator.send_json_to(
        {"message": "update"}
    )  # This part in consumer is just a pass, but let's test the receive->send loop if I implemented it?
    # Wait, my consumer receive method only handles auth. It doesn't echo "update".
    # The consumer has a `game_update` method that sends to the group.
    # To test receiving "update", I should send a group message.

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        "game_123", {"type": "game_update", "message": "update"}
    )

    response = await communicator.receive_json_from()
    assert response == {"message": "update"}

    await communicator.disconnect()
