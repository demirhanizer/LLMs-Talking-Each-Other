import streamlit as st
import requests

BASE_API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Multi-LLM Interaction", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "token" not in st.session_state:
    st.session_state.token = None

def do_login(username, password):
    try:
        response = requests.post(
            f"{BASE_API_URL}/api/token/",
            json={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            tokens = response.json()
            st.session_state.token = tokens["access"]
            st.session_state.logged_in = True
            st.rerun()  # Changed from experimental_rerun
        else:
            st.error("Login failed. Please check your credentials.")
    except Exception as e:
        st.error(f"Error logging in: {e}")

def login_page():
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if username.strip() and password.strip():
                do_login(username, password)
            else:
                st.warning("Please fill in both username and password.")

def home_page():
    st.title("Home Page")
    st.write("You are now logged in! Use the sidebar to navigate.")

def logout():
    st.session_state.logged_in = False
    st.session_state.token = None
    st.rerun()  # Changed from experimental_rerun

def logout_button():
    if st.button("Logout"):
        logout()

if not st.session_state.logged_in:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        [data-testid="stAppViewContainer"] {
            margin-left: 0;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    login_page()
else:
    home_page()
    logout_button()