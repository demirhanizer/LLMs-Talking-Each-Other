# chat/consumers.py

import json
import urllib.parse
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import AccessToken
from .models import Message, LLMPersona
import logging

logger = logging.getLogger(__name__)

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from chat.models import LLMPersona
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings


class LLMWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.token = self.scope['query_string'].decode('utf-8').split("token=")[-1]
        self.persona_name = self.scope['path'].split('/')[-2]  # Extract persona name from URL

        try:
            # Decode and validate JWT token
            decoded_token = jwt_decode(self.token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_token.get("user_id")
            self.user = await self.get_user(user_id)

            # Validate persona
            if not await self.validate_persona(self.persona_name):
                await self.close(code=403)
                return

            # Accept WebSocket connection
            await self.accept()

        except (InvalidToken, TokenError, KeyError):
            await self.close(code=403)

    async def disconnect(self, close_code):
        # Handle disconnect
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get("message", "")
            response = f"Echo: {message}"  # Replace with LLM response logic
            await self.send(text_data=json.dumps({"response": response}))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))

    @staticmethod
    async def get_user(user_id):
        try:
            return await User.objects.aget(id=user_id)
        except User.DoesNotExist:
            return None

    async def validate_persona(self, persona_name):
        try:
            await LLMPersona.objects.aget(name=persona_name)
            return True
        except LLMPersona.DoesNotExist:
            return False


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract the JWT token from the query string
        query_string = self.scope['query_string'].decode()
        query_params = urllib.parse.parse_qs(query_string)
        token_list = query_params.get('token', [])
        token = token_list[0] if token_list else None
        if not token:
            logger.error("Token not found in query string. Closing connection.")
            await self.close()
            return

        self.user = await self.get_user(token)
        if self.user is None:
            logger.error("User authentication failed. Closing connection.")
            await self.close()
            return

        self.persona_name = self.scope['url_route']['kwargs'].get('llm', None)
        if not self.persona_name:
            logger.error("Persona name not found in URL. Closing connection.")
            await self.close()
            return

        self.persona = await self.get_persona(self.user, self.persona_name)

        self.room_group_name = f'persona_{self.persona_name}_{self.user.username}'

        # Join the group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"User {self.user.username} connected to {self.room_group_name}")

    async def disconnect(self, close_code):

        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"User {self.user.username} disconnected from {self.room_group_name}")

    async def receive(self, text_data):
        logger.info(f"Received message: {text_data}")
        try:
            text_data_json = json.loads(text_data)
            message_content = text_data_json.get('message', '')

            await self.save_message(
                sender=self.user,
                persona=self.persona,
                content=message_content,
                is_from_user=True
            )

            llm_response = f"Echo: {message_content}"

            await self.save_message(
                sender=None,  # No sender for LLM messages
                persona=self.persona,
                content=llm_response,
                is_from_user=False
            )

            await self.send(text_data=json.dumps({
                'message': llm_response
            }))

        except json.JSONDecodeError:

            error_message = "Invalid message format. Please send a valid JSON."
            logger.error(f"JSONDecodeError: {error_message}")
            await self.send(text_data=json.dumps({
                'error': error_message
            }))

    @database_sync_to_async
    def get_user(self, token):
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = User.objects.get(id=user_id)
            return user
        except Exception as e:
            logger.error(f"Token authentication failed: {e}")
            return None

    @database_sync_to_async
    def get_persona(self, user, persona_name):
        persona, created = LLMPersona.objects.get_or_create(
            user=user,
            name=persona_name,
            defaults={'personality_traits': {}}
        )
        if created:
            logger.info(f"Created new persona '{persona_name}' for user '{user.username}'")
        else:
            logger.info(f"Retrieved existing persona '{persona_name}' for user '{user.username}'")
        return persona

    @database_sync_to_async
    def save_message(self, sender, persona, content, response=None, is_from_user=True):
        Message.objects.create(
            sender=sender,
            persona=persona,
            content=content,
            response=response,
            is_from_user=is_from_user
        )
import json
import requests
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from chat.models import LLMPersona
from asgiref.sync import sync_to_async

# Helper function to add personas to database
@sync_to_async
def sync_personas_with_database(personas):
    admin_user, created = User.objects.get_or_create(
        username="admin",
        defaults={"email": "admin@example.com", "is_staff": True, "is_superuser": True}
    )
    if created:
        admin_user.set_password("admin123")
        admin_user.save()

    # Sync each persona with the database
    for persona in personas:
        LLMPersona.objects.update_or_create(
            user=admin_user,
            name=persona["name"],
            defaults={"personality_traits": persona.get("traits", {})}
        )

class LLMWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract query parameters
        query_params = parse_qs(self.scope["query_string"].decode())
        token = query_params.get("token", [None])[0]
        llm_name = self.scope["path"].split("/")[-2]

        # Fetch personas from `get_all_personas` endpoint
        try:
            response = requests.get(
                "http://127.0.0.1:8000/get_all_personas/",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                personas = response.json().get("personas", [])
                await sync_personas_with_database(personas)  # Sync personas to the database
            else:
                await self.close(code=403)
                return
        except Exception as e:
            print(f"Error fetching personas: {e}")
            await self.close(code=403)
            return

        # Validate the requested LLM name
        try:
            persona = await sync_to_async(LLMPersona.objects.get)(name=llm_name)
            self.persona = persona
            await self.accept()
        except LLMPersona.DoesNotExist:
            await self.close(code=403)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message", "")

        # Simulated LLM response
        response = f"Echo from {self.persona.name}: {message}"

        # Send response back to the client
        await self.send(text_data=json.dumps({"response": response}))
