import streamlit as st
import requests
import asyncio
import websockets
import json

BASE_API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="User-LLM Chat", layout="wide")

st.markdown("""
<style>
body {
    background: linear-gradient(to bottom right, #1e1e1e, #333333);
    color: #ffffff;
    font-family: "Helvetica", sans-serif;
}
.sidebar .sidebar-content {
    background: #2d2d2d;
    color: #ffffff;
}
.stTextInput>div>div>input {
    background-color: #444444 !important;
    color: #ffffff !important;
    border-radius: 5px;
    border: 1px solid #666666;
    padding: 10px;
}
.stButton>button {
    background: #4caf50;
    color: white;
    border-radius: 5px;
    border:none;
    padding:10px 20px;
    font-weight:bold;
    cursor:pointer;
    transition: background 0.3s ease;
}
.stButton>button:hover {
    background:#3e8e41;
}
h1, h2, h3, h4 {
    font-weight: 600;
}
hr {
    border: 1px solid #444444;
    margin-top: 2rem;
    margin-bottom: 2rem;
}
.info-text {
    color: #cccccc;
    font-size: 1rem;
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

# Giriş kontrolü
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Authentication failed. Please go back to the main page and log in.")
    st.stop()

def fetch_available_llms(token=None):
    """Fetches available LLM personas."""
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

async def send_message_via_websocket(persona_name, message, token=None):
    """Sends message via WebSocket and returns the response."""
    websocket_uri = f"ws://127.0.0.1:8001/ws/llm/{persona_name}/"
    if token:
        websocket_uri += f"?token={token}"

    async with websockets.connect(websocket_uri) as websocket:
        ws_message = {"persona": persona_name, "message": message}
        await websocket.send(json.dumps(ws_message))
        response = await websocket.recv()
        return json.loads(response)

def user_llm_chat():
    """User-to-LLM chat page."""
    st.title("User-LLM Chat")
    personas = fetch_available_llms(st.session_state.token)
    if personas:
        selected_persona = st.selectbox("Select Persona", personas)
        st.write(f"**Selected Persona:** {selected_persona}")

        user_message = st.text_input("Enter your message", key="user_message")
        if st.button("Send Message"):
            if selected_persona and user_message.strip():
                try:
                    response = asyncio.run(
                        send_message_via_websocket(
                            persona_name=selected_persona,
                            message=user_message,
                            token=st.session_state.token
                        )
                    )
                    st.write(f"**Response:** {response.get('response', 'No response')}")
                except Exception as e:
                    st.error(f"Error during WebSocket communication: {e}")
            else:
                st.error("Please select a persona and enter a message.")
    else:
        st.error("No personas available. Please create one in the backend.")

user_llm_chat()
