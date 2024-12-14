import streamlit as st
import requests
from utils import get_response_from_llm, get_character_profiles

# Page configuration
st.set_page_config(page_title="AI Character Interaction", layout="wide")

# Load custom CSS
with open("custom.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Sidebar: Character Selection
st.sidebar.title("Choose Your Character")
characters = get_character_profiles()

# Display character selection as buttons with profile images
selected_character = st.sidebar.radio(
    "Select a character to chat with:",
    [char['name'] for char in characters],
    format_func=lambda x: f"🧑‍🎓 {x}"
)

# Retrieve the selected character's information
character = next(char for char in characters if char['name'] == selected_character)

# Show character information
st.sidebar.image(character['image'], width=150)
st.sidebar.markdown(f"### {character['name']}")
st.sidebar.markdown(f"**About**: {character['description']}")

# Chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

st.title(f"💬 Chat with {character['name']}")

# Chat box (Message History)
chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_history:
        if message['sender'] == 'user':
            st.markdown(f"<div class='user-message'>{message['message']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='ai-message'><img src='{character['image']}' width='40' class='avatar'><div>{message['message']}</div></div>", unsafe_allow_html=True)

# Input message
st.markdown("---")
st.markdown("### Type your message")
with st.form(key="user_input_form", clear_on_submit=True):
    user_input = st.text_input("", placeholder="Type your message here...")
    submit_button = st.form_submit_button(label="Send")

# Send message to LLM and receive response
if submit_button and user_input:
    st.session_state.chat_history.append({"sender": "user", "message": user_input})
    response = get_response_from_llm(user_input, character['name'])
    st.session_state.chat_history.append({"sender": 'llm', "message": response})
    st.experimental_rerun()
