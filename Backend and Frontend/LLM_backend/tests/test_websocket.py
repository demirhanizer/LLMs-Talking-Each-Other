import asyncio
import websockets
import json

async def test_websocket():
    llm = ""  # Replace with the LLM instance you want to test
    uri = f"ws://localhost:8000/ws/llm/{llm}/"  # WebSocket URL

    async with websockets.connect(uri) as websocket:
        # Send a test message to the WebSocket server
        test_message = json.dumps({
            'message': 'Hello, LLM!'
        })
        await websocket.send(test_message)
        print(f"Sent: {test_message}")

        # Wait for the server's response
        response = await websocket.recv()
        print(f"Received: {response}")

# Run the test client
asyncio.get_event_loop().run_until_complete(test_websocket())
