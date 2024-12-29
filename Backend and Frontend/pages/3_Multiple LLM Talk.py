import streamlit as st
import requests
import json
import asyncio
import websockets

# Sabitler
FLASK_API_URL = "http://10.3.0.96:5000/generate_multi_llm"  # Flask API URL
BASE_API_URL = "http://127.0.0.1:8000"  # Base API URL for fetching personas

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "token" not in st.session_state:
    st.session_state.token = None

if not st.session_state.logged_in:
    st.warning("Authentication failed. Please go back to the main page and log in.")
    st.stop()



st.set_page_config(page_title="LLM-LLM Interaction", layout="wide")

st.markdown(
    """
    <style>
    body {
        background-color: #121212;
        color: #ffffff;
        font-family: "Helvetica", sans-serif;
    }
    .sidebar .sidebar-content {
        background: #1E1E1E;
        color: #ffffff;
    }
    h1, h2, h3, h4 {
        font-weight: 600;
    }
    .stTextInput>div>div>input,
    .stTextArea>div>textarea {
        background-color: #2b2b2b !important;
        color: #ffffff !important;
        border-radius: 5px;
        border: 1px solid #555555;
        padding: 10px;
    }
    .stButton>button {
        background: #333333;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
        cursor: pointer;
        transition: background 0.3s ease;
    }
    .stButton>button:hover {
        background: #444444;
    }
    .stSlider label {
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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

    st.session_state.llms = fetch_available_llms(st.session_state.get("token"))

async def send_message_via_websocket(action, selected_personas, claim, token=None, iterations=None):
    """
    Sends a multi-LLM interaction request to the WebSocket server.
    """
    websocket_uri = "ws://127.0.0.1:8001/ws/multi_llm/"
    if token:
        websocket_uri += f"?token={token}"

    async with websockets.connect(websocket_uri) as websocket:
        ws_message = {
            "action": action,
            "selected_personas": selected_personas,  # List of personas
            "claim": claim,  # Initial claim/message
            "iterations": iterations
        }
        await websocket.send(json.dumps(ws_message))  # Send request as JSON
        response = await websocket.recv()  # Receive response
        return json.loads(response)  # Parse JSON response

def call_multi_llm_api(selected_personas, claim):
    """
    Sends a POST request to the Flask API to start a multi-LLM interaction.

    Parameters:
        selected_personas (list): List of persona names for the interaction.
        claim (str): Initial claim/message to start the conversation.
        iterations (int): Number of iterations for the conversation.

    Returns:
        dict: The parsed response containing the conversation or an error.
    """
    payload = {
        "selected_personas": selected_personas,
        "claim": claim,
    }

    try:
        # Send POST request to the Flask API
        response = requests.post(FLASK_API_URL, json=payload, timeout=360)
        if response.status_code == 200:
            # Parse and return JSON response
            return response.json()  # Expecting {"conversation": [...]}
        else:
            error_message = f"API Error: {response.status_code} - {response.text}"
            st.error(error_message)
            return {"error": error_message}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error: {str(e)}"
        st.error(error_message)
        return {"error": error_message}


def main():
    st.title("LLM-LLM Interaction")

    # Update LLM options and default selections here
    llm_options = ["hilalkaplan", "ismailsaymaz", "mehmettezkan", "q_melihasik", "q_nagehanalci"]
    default_llms = ["hilalkaplan", "ismailsaymaz", "mehmettezkan", "q_melihasik", "q_nagehanalci"]  # Choose default personas you prefer

    # Let users select from updated options
    selected_llms = st.multiselect(
        "Select LLM(s) (up to 5)",
        llm_options,
        default=default_llms,
        help="Choose up to 5 LLMs."
    )

    initial_message = st.text_area("Enter the initial message to start the conversation")

    if st.button("Start Interaction"):
        if len(selected_llms) < 2:
            st.error("Please select at least 2 LLMs.")
            return

        if not initial_message.strip():
            st.error("Please enter a valid initial message.")
            return

        # Call the Flask API
        with st.spinner("LLMs are interacting..."):
            result = call_multi_llm_api(selected_llms, initial_message)

        if result and "conversation" in result:
            st.markdown("---")
            st.subheader("Conversation Flow")
            conversation = result["conversation"]
            for item in conversation:
                llm_name = item["persona"]  # Update key to match persona field in the response
                llm_response = item["response"]
                st.write(f"**{llm_name}**: {llm_response}")
        else:
            st.warning("No conversation returned from the API.")


if __name__ == "__main__":
    main()
