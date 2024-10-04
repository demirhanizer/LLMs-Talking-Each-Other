# websocket_client.py

import asyncio
import websockets
import json

async def test_websocket():
    token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzI4MDUwNzE5LCJpYXQiOjE3MjgwNDcxMTksImp0aSI6ImJiNTNhYzQyNjY4ZjRmNGNiZTBiNGMyMmFlODgyN2RmIiwidXNlcl9pZCI6Mn0.-z9GnwZUtgplvd6O9dlStFKIMVlaqrnExpMC4qDDB5Q'  # Replace with your JWT access token
    uri = f"ws://localhost:8001/ws/llm/gpt-3/?token={token}"

    async with websockets.connect(uri) as websocket:
        # Send a message to the server
        message = {'message': 'Hello, LLM!'}
        await websocket.send(json.dumps(message))
        print(f"Sent: {message}")

        # Receive a response from the server
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Received: {data}")

asyncio.get_event_loop().run_until_complete(test_websocket())
