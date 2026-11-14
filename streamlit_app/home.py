"""
Login / sign-up page.
"""

import streamlit as st

from utils.api_client import create_user, login_user

st.set_page_config(page_title="Adapt-RAG - Login", layout="centered", initial_sidebar_state="collapsed")
st.markdown("<style>[data-testid='stSidebarNav']{display:none}</style>", unsafe_allow_html=True)

if "token" in st.session_state:
    st.switch_page("pages/chat.py")

st.title("🔐 Welcome to Adapt-RAG")

with st.form("auth_form"):
    username = st.text_input("Username")
    password = st.text_input("Password (min 8 characters)", type="password")
    mode = st.radio("Choose action:", ["Login", "Create Account"], horizontal=True)
    submit = st.form_submit_button("Submit")

if submit:
    if mode == "Create Account":
        _, err = create_user(username, password)
        if err:
            st.error(f"Sign-up failed: {err}")
        else:
            st.success("Account created. Choose Login and submit again.")
    else:
        data, err = login_user(username, password)
        if err:
            st.error(f"Login failed: {err}")
        else:
            st.session_state["token"] = data["token"]
            st.session_state["username"] = username
            st.switch_page("pages/chat.py")
