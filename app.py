import streamlit as st
import requests
import asyncio
import websockets
import json

# Base API URL
BASE_API_URL = "http://127.0.0.1:8000"

# Streamlit configuration
st.set_page_config(page_title="WebSocket Messaging with Multiple LLMs", layout="centered")

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "token" not in st.session_state:
    st.session_state.token = None


# Function to log in and retrieve the token
def login(username, password):
    try:
        response = requests.post(
            f"{BASE_API_URL}/api/token/",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            tokens = response.json()
            st.session_state.token = tokens["access"]
            st.session_state.logged_in = True
            st.success("Login successful!")
        else:
            st.error("Login failed. Please check your credentials.")
    except Exception as e:
        st.error(f"Error logging in: {e}")


# Function to fetch available LLM personas
def fetch_available_llms(token=None):
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Send GET request to fetch personas
        response = requests.get(
            f"{BASE_API_URL}/get_all_personas/",
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            return [persona["name"] for persona in data.get("personas", [])]
        elif response.status_code == 404:
            st.error("No personas found. Please create a persona first.")
        else:
            st.error(f"Error fetching personas: {response.status_code}")
    except Exception as e:
        st.error(f"Error fetching personas: {e}")
    return []


# Function to handle WebSocket messaging
async def send_message_via_websocket(persona_name, message, token=None):
    # Construct the WebSocket URI
    websocket_uri = f"ws://127.0.0.1:8001/ws/llm/{persona_name}/"
    if token:
        websocket_uri += f"?token={token}"

    async with websockets.connect(websocket_uri) as websocket:
        # Construct the WebSocket message
        ws_message = {"persona": persona_name, "message": message}
        await websocket.send(json.dumps(ws_message))  # Send message
        response = await websocket.recv()  # Wait for the server's response
        return json.loads(response)  # Return parsed response


# Streamlit Layout
st.title("WebSocket Messaging with Multiple LLMs")

# Step 1: Log in (Optional)
st.subheader("Step 1: Log In (Optional)")
username = st.text_input("Enter Username", key="username_login")
password = st.text_input("Enter Password", type="password", key="password_login")

if st.button("Login"):
    login(username, password)

# Step 2: Select Persona
st.subheader("Step 2: Select Persona")
personas = fetch_available_llms(st.session_state.token if st.session_state.logged_in else None)

if personas:
    selected_persona = st.selectbox("Available Personas", personas)
    st.write(f"Selected Persona: {selected_persona}")

    # Step 3: Messaging
    st.subheader("Step 3: Chat with LLM")
    user_message = st.text_input("Enter your message", key="user_message")
    if st.button("Send Message"):
        if selected_persona and user_message.strip():
            try:
                # Run WebSocket communication
                response = asyncio.run(
                    send_message_via_websocket(
                        persona_name=selected_persona,
                        message=user_message,
                        token=st.session_state.token if st.session_state.logged_in else None
                    )
                )
                st.write(f"LLM Response: {response.get('response', 'No response')}")
            except Exception as e:
                st.error(f"Error during WebSocket communication: {e}")
        else:
            st.error("Please select a persona and enter a message.")
else:
    st.error("No personas available. Please create one in the backend.")
