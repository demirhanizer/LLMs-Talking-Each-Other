# chat/consumers.py

import json
import logging
import urllib.parse
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings
from asgiref.sync import sync_to_async
import aiohttp
from .models import Message, LLMPersona

logger = logging.getLogger(__name__)

class LLMWebSocketConsumer(AsyncWebsocketConsumer):
    


    
    async def call_flask_llm_to_llm(self, prompt_1, prompt_2, iterations):
        llm_to_llm_url = "http://10.3.0.96:5000/generate_llm_to_llm"
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "prompt_1": prompt_1,
                    "prompt_2": prompt_2,
                    "iterations": iterations
                }
                async with session.post(llm_to_llm_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Check if the API response contains a valid conversation
                        if "conversation" in result and isinstance(result["conversation"], list):
                            return result["conversation"]
                        else:
                            raise ValueError("Invalid API response format: Missing or invalid 'conversation' key.")
                    else:
                        raise ValueError(f"Flask API returned an error with status code: {response.status}")
        except Exception as e:
            logger.error(f"Error during Flask API call: {e}")
            return [{"error": str(e)}]

    async def connect(self):
        try:
           
            # Extract token from query string
            query_string = self.scope['query_string'].decode('utf-8')
            query_params = urllib.parse.parse_qs(query_string)
            self.token = query_params.get("token", [None])[0]  # Extract token or set to None if missing

            # Extract persona name from the URL path
            path_parts = self.scope['path'].rstrip('/').split('/')
            if len(path_parts) >= 2:
                self.persona_name = path_parts[-1]  # Get the last part of the path as the persona name
            else:
                logger.error("Persona name could not be extracted from URL.")
                await self.close(code=400)
                return

            logger.info(f"Extracted persona name: {self.persona_name}")


            # Decode and validate the JWT token
            decoded_token = jwt_decode(self.token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_token.get("user_id")
            self.user = await self.get_user(user_id)

            # Validate persona existence
            if not await self.validate_persona(self.persona_name):
                await self.close(code=403)
                return

            # Accept WebSocket connection
            await self.accept()
        except (InvalidToken, TokenError, KeyError, AttributeError) as e:
            logger.error(f"Error during WebSocket connection aaaaaaa: {e}")
            await self.close(code=403)

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"User {getattr(self.user, 'username', 'Unknown')} disconnected from {getattr(self, 'room_group_name', 'Unknown')}")

    async def receive(self, text_data):
        try:
            logger.info(f"Received message: {text_data}")
            data = json.loads(text_data)
            action = data.get("action", "message")

            if action == "message":
                await self.handle_message_action(data)
            elif action == "llm_to_llm":
                await self.handle_llm_to_llm_action(data)
            else:
                await self.send(text_data=json.dumps({"error": f"Invalid action: {action}"}))
        except json.JSONDecodeError:
            error_message = "Invalid JSON format. Please send a valid JSON."
            logger.error(f"JSON Decode Error: {error_message}")
            await self.send(text_data=json.dumps({"error": error_message}))
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def handle_message_action(self, data):
        message = data.get("message", "").strip()
        if not message:
            await self.send(text_data=json.dumps({"error": "No message provided"}))
            logger.warning("No message provided in client request.")
            return

        # Save incoming user message
        await self.save_message(sender=self.user, persona=self.persona, content=message, is_from_user=True)

        # Send the message to the Flask LLM server
        llm_url = "http://10.3.0.96:5000/generate"
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"prompt": message, "persona_name": self.persona_name}
                logger.info(f"Sending request to LLM server: {llm_url} with payload: {payload}")
                async with session.post(llm_url, json=payload) as response:
                    if response.status == 200:
                        llm_data = await response.json()
                        llm_response = llm_data.get("response", "No response from LLM")
                    else:
                        llm_response = f"Error from LLM server: {response.status}"
                        logger.error(f"LLM server returned error {response.status}: {await response.text()}")

            # Save LLM's response
            await self.save_message(sender=None, persona=self.persona, content=llm_response, is_from_user=False)

            # Send the response back to the client
            await self.send(text_data=json.dumps({"response": llm_response}))
        except Exception as e:
            error_message = f"Error communicating with LLM server: {str(e)}"
            logger.error(error_message)
            await self.send(text_data=json.dumps({"error": error_message}))



    async def handle_llm_to_llm_action(self, data):
        prompt_1 = data.get("prompt_1", "")
        prompt_2 = data.get("prompt_2", "")
        iterations = data.get("iterations", 3)

        if not prompt_1 or not prompt_2:
            await self.send(text_data=json.dumps({"error": "Two initial prompts are required"}))
            return

        conversation = await self.call_flask_llm_to_llm(prompt_1, prompt_2, iterations)
        if "error" in conversation[0]:
            logger.error(f"Error during LLM-to-LLM interaction: {conversation[0]['error']}")
            await self.send(text_data=json.dumps({"error": conversation[0]["error"]}))
        else:
            await self.send(text_data=json.dumps({"conversation": conversation}))

    @database_sync_to_async
    def save_message(self, sender, persona, content, is_from_user=True):
        Message.objects.create(sender=sender, persona=persona, content=content, is_from_user=is_from_user)

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} does not exist.")
            return None

    @database_sync_to_async
    def validate_persona(self, persona_name):
        try:
            LLMPersona.objects.get(name=persona_name)
            return True
        except LLMPersona.DoesNotExist:
            logger.error(f"Persona '{persona_name}' does not exist.")
            return False


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Parse query string for JWT token
        query_params = urllib.parse.parse_qs(self.scope['query_string'].decode())
        token_list = query_params.get('token', [])
        token = token_list[0] if token_list else None

        if not token:
            logger.error("Token not found in query string. Closing connection.")
            await self.close()
            return

        # Authenticate user
        self.user = await self.get_user(token)
        if self.user is None:
            logger.error("User authentication failed. Closing connection.")
            await self.close()
            return

        # Get persona name
        self.persona_name = self.scope['url_route']['kwargs'].get('llm', None)
        if self.persona_name:
            self.persona_name = self.persona_name.rstrip('/')
        if not self.persona_name:
            logger.error("Persona name not found in URL. Closing connection.")
            await self.close()
            return

        self.persona = await self.get_persona(self.user, self.persona_name)

        # Create group name
        clean_persona_name = re.sub(r'[^a-zA-Z0-9_\-.]', '_', self.persona_name)
        clean_username = re.sub(r'[^a-zA-Z0-9_\-.]', '_', self.user.username)
        self.room_group_name = f'persona_{clean_persona_name}_{clean_username}'[:100]

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
        try:
            logger.info(f"Received message: {text_data}")
            data = json.loads(text_data)
            action = data.get("action", "message")

            if action == "message":
                await self.handle_message(data)
            elif action == "llm_to_llm":
                await self.handle_llm_to_llm(data)
            elif action == "multi_llm":
                await self.handle_multi_llm_action(data)
            else:
                await self.send(text_data=json.dumps({"error": "Invalid action type"}))

        except json.JSONDecodeError:
            logger.error("JSON Decode Error: Invalid message format.")
            await self.send(text_data=json.dumps({"error": "Invalid message format. Please send a valid JSON."}))

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await self.send(text_data=json.dumps({"error": str(e)}))


    async def handle_multi_llm_action(self, data):
        MULTI_LLM_URL = "http://10.3.0.96:5000/generate_multi_llm"
        """
        Handles multi-LLM interaction by sending a POST request to the Flask endpoint.
        Expected JSON format:
            {
                "selected_personas": ["persona1", "persona2", "persona3", ...],
                "claim": "Initial user message",
                "iterations": 5
            }
        """
        # Extract required fields from the data
        selected_personas = data.get("selected_personas", [])
        claim = data.get("claim", "").strip()
        iterations = data.get("iterations", 5)

        # Validate inputs
        if not selected_personas:
            await self.send(text_data=json.dumps({"error": "You must provide 'selected_personas'"}))
            return
        if not claim:
            await self.send(text_data=json.dumps({"error": "You must provide a 'claim'"}))
            return
        if not isinstance(iterations, int) or iterations <= 0:
            await self.send(text_data=json.dumps({"error": "'iterations' must be a positive integer"}))
            return

        # Make a POST request to the Flask API
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "selected_personas": selected_personas,
                    "claim": claim,
                    "iterations": iterations
                }
                logger.info(f"Sending Multi-LLM request to {MULTI_LLM_URL} with payload: {payload}")
                async with session.post(MULTI_LLM_URL, json=payload) as response:
                    logger.info(f"Multi-LLM Server HTTP Status: {response.status}")
                    
                    if response.status == 200:
                        llm_data = await response.json()
                        # Extract conversation from the response
                        conversation = llm_data.get("conversation", [])

                        if isinstance(conversation, list):
                            # Optionally save each message to the database
                            for msg in conversation:
                                await self.save_message(
                                    sender=None,
                                    persona=msg.get("persona", "unknown"),
                                    content=msg.get("response", "No response"),
                                    is_from_user=False
                                )
                            # Send the conversation back to the client
                            await self.send(text_data=json.dumps({"conversation": conversation}))
                        else:
                            error_message = "Invalid conversation format from Flask API."
                            logger.error(error_message)
                            await self.send(text_data=json.dumps({"error": error_message}))
                    else:
                        error_message = f"Multi-LLM interaction failed with status {response.status}"
                        logger.error(error_message)
                        await self.send(text_data=json.dumps({"error": error_message}))

        except Exception as e:
            error_message = f"Error during Multi-LLM interaction: {str(e)}"
            logger.error(error_message)
            await self.send(text_data=json.dumps({"error": error_message}))


    async def handle_message(self, data):
        message = data.get("message", "").strip()  # Remove leading/trailing whitespace
        if not message:
            error_message = "No message provided"
            logger.warning(error_message)
            await self.send(text_data=json.dumps({"error": error_message}))
            return

        try:
            # 1) Save the user's message to the database
            await self.save_message(
                sender=self.user,
                persona=self.persona,
                content=message,
                is_from_user=True
            )
            logger.info(f"Saved message from user '{self.user.username}' to DB: {message}")

        except Exception as e:
            error_message = f"Failed to save user message to DB: {e}"
            logger.error(error_message)
            await self.send(text_data=json.dumps({"error": error_message}))
            return

        # 2) Send the message to the Flask LLM server
        llm_url = "http://10.3.0.96:5000/generate"
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"prompt": message, "persona_name": self.persona.name}
                logger.info(f"Sending request to LLM server at {llm_url} with payload: {payload}")
                async with session.post(llm_url, json=payload) as response:
                    if response.status == 200:
                        try:
                            llm_data = await response.json()
                            llm_response = llm_data.get("response", "No response from LLM")
                            logger.info(f"Received response from LLM server: {llm_response}")
                        except json.JSONDecodeError as e:
                            llm_response = f"Error decoding LLM response JSON: {e}"
                            logger.error(llm_response)
                    else:
                        llm_response = f"LLM server returned status {response.status}: {await response.text()}"
                        logger.error(llm_response)
        except Exception as e:
            llm_response = f"Error communicating with LLM server: {e}"
            logger.error(llm_response)

        # 3) Save the LLM's response to the database
        try:
            await self.save_message(
                sender=None,
                persona=self.persona,
                content=llm_response,
                is_from_user=False
            )
            logger.info(f"Saved LLM response to DB: {llm_response}")
        except Exception as e:
            error_message = f"Failed to save LLM response to DB: {e}"
            logger.error(error_message)
            await self.send(text_data=json.dumps({"error": error_message}))
            return

        # 4) Send the response back to the client
        try:
            logger.info(f"Sending response to client: {llm_response}")
            await self.send(text_data=json.dumps({"response": llm_response}))
        except Exception as e:
            logger.error(f"Failed to send response to client: {e}")

    async def handle_llm_to_llm(self, data):
        prompt_1 = data.get("prompt_1", "").strip()
        prompt_2 = data.get("prompt_2", "").strip()
        iterations = data.get("iterations", 3)

        if not prompt_1 or not prompt_2:
            error_message = "Two initial prompts are required"
            logger.warning(error_message)
            await self.send(text_data=json.dumps({"error": error_message}))
            return

        # Ensure persona_name is included in the payload
        llm_to_llm_url = "http://10.3.0.96:5000/generate_llm_to_llm"
        try:
            payload = {
                "prompt_1": prompt_1,
                "prompt_2": prompt_2,
                "iterations": iterations,
                "persona_name": self.persona.name  # Include persona_name
            }
            logger.info(f"Sending LLM-to-LLM request to {llm_to_llm_url} with payload: {payload}")

            async with aiohttp.ClientSession() as session:
                async with session.post(llm_to_llm_url, json=payload) as response:
                    logger.info(f"LLM-to-LLM Server HTTP Status: {response.status}")

                    if response.status == 200:
                        try:
                            llm_data = await response.json()
                            conversation = llm_data.get("conversation", [])
                            
                            if isinstance(conversation, list):
                                # Log each message in the conversation
                                for idx, message in enumerate(conversation):
                                    logger.info(f"Conversation message {idx}: {message}")

                                # Send the entire conversation to the client
                                await self.send(text_data=json.dumps({"conversation": conversation}))
                            else:
                                error_message = "Invalid conversation format received from Flask API"
                                logger.error(error_message)
                                await self.send(text_data=json.dumps({"error": error_message}))
                        except json.JSONDecodeError as e:
                            error_message = f"Error decoding LLM-to-LLM response JSON: {e}"
                            logger.error(error_message)
                            await self.send(text_data=json.dumps({"error": error_message}))
                    else:
                        error_message = f"LLM-to-LLM interaction failed with status {response.status}: {await response.text()}"
                        logger.error(error_message)
                        await self.send(text_data=json.dumps({"error": error_message}))

        except Exception as e:
            error_message = f"Error during LLM-to-LLM interaction: {str(e)}"
            logger.error(error_message)
            await self.send(text_data=json.dumps({"error": error_message}))


    @database_sync_to_async
    def save_message(self, sender, persona, content, is_from_user=True):
        Message.objects.create(
            sender=sender,
            persona=persona,
            content=content,
            is_from_user=is_from_user
        )

    @database_sync_to_async
    def get_user(self, token):
        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            return User.objects.get(id=user_id)
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

