import streamlit as st

# Kullanıcı giriş yapmamışsa doğrudan ana sayfaya yönlendirilebilir.
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.info("You are not logged in.")
    st.stop()

# Logout işlemi
st.session_state.logged_in = False
st.session_state.token = None

# Clear query parameters to remove logged_in flag
st.query_params.clear()
st.success("You have been logged out successfully.")
st.write("Please return to the main page to log in again.")
