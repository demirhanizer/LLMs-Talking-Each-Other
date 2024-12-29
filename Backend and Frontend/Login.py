import streamlit as st
import requests
import asyncio
import websockets
import json

# Base API URL
BASE_API_URL = "http://127.0.0.1:8000"

# Streamlit configuration
st.set_page_config(page_title="Multi-LLM Interaction", layout="wide")

# Custom CSS for styling
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

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "token" not in st.session_state:
    st.session_state.token = None

params = st.query_params

if params.get("logged_in") == "true":
    st.session_state.logged_in = True

def login(username, password):
    """Logs in and saves the token."""
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
            # Previously setting query params is removed.
        else:
            st.error("Login failed. Please check your credentials.")
    except Exception as e:
        st.error(f"Error logging in: {e}")

def login_page():
    st.title("LLM'S TALKING TO EACH OTHER!!!!!!")
    username = st.text_input("Enter Username", key="username_login")
    password = st.text_input("Enter Password", type="password", key="password_login")

    if st.button("Login"):
        if username.strip() and password.strip():
            login(username, password)
        else:
            st.warning("Please fill in both username and password.")

if not st.session_state.logged_in:
    st.sidebar.warning("Please log in to access the other pages.")
    login_page()
else:
    st.title("LLM'S TALKING TO EACH OTHER!!!!!!!!!!!!!!")
    st.write("Use the sidebar to navigate to the other sections.")
