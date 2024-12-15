import asyncio
import websockets
import json

async def test_websocket():
    # Replace with your JWT token
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MzQyMTQ1MjcsImlhdCI6MTczNDIxMDkyN30.yVnhI66lGiFa-ExMzAuzR4AODPU33Bpj1FX-U-vE-D4"  # Generate using generate_token.py
    uri = f"ws://127.0.0.1:8001/ws/llm/gpt-3/?token={token}"

    async with websockets.connect(uri) as websocket:
        # Send a message to the server
        message = {"message": "Hello, LLM!"}
        await websocket.send(json.dumps(message))
        print(f"Sent: {message}")

        # Receive a response from the server
        response = await websocket.recv()
        print(f"Received: {response}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
