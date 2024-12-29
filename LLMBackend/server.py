from fastapi import FastAPI, WebSocket, Query, HTTPException
import jwt
import requests

app = FastAPI()

# Secret key for JWT validation
SECRET_KEY = "your_secret_key"

# Endpoint to fetch personas (simulate fetching from a database)
PERSONA_SERVICE_URL = "http://127.0.0.1:8000/get_persona/"

def get_available_personas():
    try:
        response = requests.get(PERSONA_SERVICE_URL)
        if response.status_code == 200:
            return response.json().get("available_llms", [])
        else:
            raise Exception(f"Error fetching personas: {response.status_code}")
    except Exception as e:
        print(f"Error fetching personas: {e}")
        return []

@app.websocket("/ws/llm/{llm_name}/")
async def websocket_endpoint(websocket: WebSocket, llm_name: str, token: str = Query(...)):
    try:
        # Fetch the list of available LLMs dynamically
        available_llms = get_available_personas()

        # Check if the requested LLM is available
        if llm_name not in available_llms:
            await websocket.close(code=4000)  # Close connection with a custom error code
            print(f"Invalid LLM name requested: {llm_name}")
            return

        # Decode and validate the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if not user_id:
            raise jwt.InvalidTokenError("User ID is missing in token")

        print(f"Connection established with user_id: {user_id} for LLM: {llm_name}")
        await websocket.accept()

        while True:
            # Receive and respond to messages
            data = await websocket.receive_text()
            print(f"Message received from {llm_name}: {data}")

            # Simulate different LLMs responding differently
            response_message = f"{llm_name} says: {data}"

            response = {"status": "success", "message": response_message}
            await websocket.send_json(response)

    except jwt.ExpiredSignatureError:
        print("Token expired")
        await websocket.close(code=4003)
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")
        await websocket.close(code=4003)
    except Exception as e:
        print(f"Unhandled error: {e}")
        await websocket.close()
