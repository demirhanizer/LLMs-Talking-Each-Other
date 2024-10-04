# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.llm = self.scope['url_route']['kwargs'].get('llm', None)

        if self.llm:
            logger.info(f"WebSocket connection for llm: {self.llm}")
            self.llm_group_name = f'llm_{self.llm}'

            # Join WebSocket group for this llm
            await self.channel_layer.group_add(
                self.llm_group_name,
                self.channel_name
            )
            await self.accept()  # Accept the connection
        else:
            logger.error("No 'llm' parameter found in the URL. Closing connection.")
            await self.close()

    async def disconnect(self, close_code):
        logger.info(f"Disconnecting WebSocket from group: {self.llm_group_name}")
        await self.channel_layer.group_discard(
            self.llm_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        logger.info(f"Received message: {text_data}")
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to the WebSocket group
        await self.channel_layer.group_send(
            self.llm_group_name,
            {
                'type': 'llm_message',
                'message': message
            }
        )

    async def llm_message(self, event):
        # Send the message to the WebSocket
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))
