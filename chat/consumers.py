# chat/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import AccessToken
from .models import Message, LLMPersona
import logging

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract the JWT token from the query string
        query_string = self.scope['query_string'].decode()
        token = query_string.split('token=')[1] if 'token=' in query_string else None
        if not token:
            await self.close()
            return

        self.user = await self.get_user(token)
        if self.user is None:
            await self.close()
            return

        # Get the persona name from the URL route
        self.persona_name = self.scope['url_route']['kwargs'].get('llm', None)
        if not self.persona_name:
            await self.close()
            return

        # Get or create the LLMPersona instance
        self.persona = await self.get_persona(self.user, self.persona_name)

        # Create a group name based on the persona
        self.room_group_name = f'persona_{self.persona_name}'

        # Join the group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"User {self.user.username} connected to {self.room_group_name}")

    async def disconnect(self, close_code):
        # Leave the group
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

            # Save the user's message to the database
            await self.save_message(
                sender=self.user,
                persona=self.persona,
                content=message_content,
                is_from_user=True
            )

            # Since we're not connecting to an LLM, we'll send an acknowledgment back
            await self.send(text_data=json.dumps({
                'message': f"Message received: {message_content}"
            }))

        except json.JSONDecodeError:
            # Handle JSON decoding error
            error_message = "Invalid message format. Please send a valid JSON."
            logger.error(f"JSONDecodeError: {error_message}")
            await self.send(text_data=json.dumps({
                'error': error_message
            }))

    @database_sync_to_async
    def get_user(self, token):
        try:
            access_token = AccessToken(token)
            user = User.objects.get(id=access_token['user_id'])
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
