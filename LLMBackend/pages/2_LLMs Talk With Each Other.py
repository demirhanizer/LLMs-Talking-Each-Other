import streamlit as st
import requests
import asyncio
import websockets
import json

# Base API URL
BASE_API_URL = "http://127.0.0.1:8000"

# Check if logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Authentication failed. Please go back to the main page and log in.")
    st.stop()
st.set_page_config(page_title="LLMs Talk With Each Other", layout="wide")

# Fetch available LLMs only once
if "llms" not in st.session_state:
    def fetch_available_llms(token=None):
        try:
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            response = requests.get(f"{BASE_API_URL}/get_all_personas/", headers=headers)

            if response.status_code == 200:
                data = response.json()
                return [persona["name"] for persona in data.get("personas", [])]
            elif response.status_code == 401:
                st.error("Authentication failed. Please log in again.")
                st.session_state.logged_in = False
            elif response.status_code == 404:
                st.error("No personas found. Please create a persona first.")
            else:
                st.error(f"Error fetching personas: {response.status_code}")
        except Exception as e:
            st.error(f"Error fetching personas: {e}")
        return []

    st.session_state.llms = fetch_available_llms(st.session_state.token)

# Function to send message via WebSocket
async def send_message_via_websocket(action, persona_1, persona_2, message, token=None, iterations=None):
    websocket_uri = f"ws://127.0.0.1:8001/ws/llm/{persona_1}/"
    if token:
        websocket_uri += f"?token={token}"

    async with websockets.connect(websocket_uri) as websocket:
        ws_message = {
            "action": action,
            "prompt_1": message,
            "prompt_2": persona_2,  # Specify the second persona name
            "iterations": iterations
        }
        await websocket.send(json.dumps(ws_message))
        response = await websocket.recv()
        return json.loads(response)

# Function to handle LLM-to-LLM interaction loop
async def llm_interaction_loop(persona_1, persona_2, initial_message, token, iterations=5):
    conversation = []

    try:
        # WebSocket call for LLM-to-LLM interaction
        response = await send_message_via_websocket(
            action="llm_to_llm",
            persona_1=persona_1,
            persona_2=persona_2,
            message=initial_message,
            token=token,
            iterations=iterations
        )

        # Display the raw WebSocket response for debugging
        st.write("WebSocket Response:", response)

        # Extract conversation from the response
        if "conversation" in response:
            conversation.extend(response["conversation"])
        else:
            st.error("Invalid response format: Missing 'conversation' key.")
    except Exception as e:
        st.error(f"Error during LLM-to-LLM interaction: {e}")
    return conversation

def llm_llm_interaction():
    st.title("LLM-LLM Interaction")
    st.write("Watch as LLMs interact with each other!")

    persona_1 = st.selectbox("Select LLM 1", st.session_state.llms)
    persona_2 = st.selectbox("Select LLM 2", st.session_state.llms)
    initial_message = st.text_input("Enter the initial message to start the conversation")
    iterations = st.slider("Number of Interaction Iterations", 1, 10, 5)

    if st.button("Start LLM Interaction"):
        if not persona_1 or not persona_2 or not initial_message:
            st.error("Please select both LLMs and provide an initial message.")
            return

        if persona_1 == persona_2:
            st.error("Please select two different LLMs.")
            return

        try:
            conversation = asyncio.run(
                llm_interaction_loop(persona_1, persona_2, initial_message, st.session_state.token, iterations)
            )
            for persona, message in conversation:
                st.write(f"{persona}: {message}")
        except Exception as e:
            st.error(f"Error during WebSocket communication aaaa: {e}")

llm_llm_interaction()
