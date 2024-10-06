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

        # Get the persona name from the URL route
        self.persona_name = self.scope['url_route']['kwargs'].get('llm', None)
        if not self.persona_name:
            logger.error("Persona name not found in URL. Closing connection.")
            await self.close()
            return

        # Get or create the LLMPersona instance
        self.persona = await self.get_persona(self.user, self.persona_name)

        # Create a group name based on the persona and user
        self.room_group_name = f'persona_{self.persona_name}_{self.user.username}'

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

            # Simulate an LLM response (echo the user's message)
            llm_response = f"Echo: {message_content}"

            # Save the LLM's response to the database
            await self.save_message(
                sender=None,  # No sender for LLM messages
                persona=self.persona,
                content=llm_response,
                is_from_user=False
            )

            # Send the LLM's response back to the client
            await self.send(text_data=json.dumps({
                'message': llm_response
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
            # Decode the JWT token to get the user ID
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            # Retrieve the user from the database
            user = User.objects.get(id=user_id)
            return user
        except Exception as e:
            logger.error(f"Token authentication failed: {e}")
            return None

    @database_sync_to_async
    def get_persona(self, user, persona_name):
        # Retrieve or create the LLMPersona for the user
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
