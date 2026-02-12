import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from game.models.game_models import Game


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]
        self.room_group_name = f"game_{self.game_id}"
        self.authenticated = False

        # Accept connection but do not join group yet
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group if joined
        if self.authenticated:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        if not self.authenticated:
            if data.get("type") == "authenticate":
                token = data.get("token")
                if await self.authenticate_user(token):
                    self.authenticated = True
                    await self.channel_layer.group_add(
                        self.room_group_name, self.channel_name
                    )
                    await self.send(text_data=json.dumps({"type": "authenticated"}))
                else:
                    await self.close()
            else:
                # Initial message must be authentication
                await self.close()
        else:
            # Handle other messages if needed
            pass

    @database_sync_to_async
    def authenticate_user(self, token_string):
        try:
            access_token = AccessToken(token_string)
            user = User.objects.get(id=access_token["user_id"])

            # Check permissions: User must be in the game or owner
            game = Game.objects.get(id=self.game_id)
            if game.owner == user or game.players.filter(user=user).exists():
                return True
            return False
        except (InvalidToken, TokenError, User.DoesNotExist, Game.DoesNotExist):
            return False

    # Receive message from room group
    async def game_update(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
