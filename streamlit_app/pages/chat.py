"""
Chat page: document upload in the sidebar, conversation in the main area.
"""

import streamlit as st

from utils.api_client import document_upload_rag, query_backend

st.set_page_config(page_title="Adapt-RAG Chat", layout="wide", initial_sidebar_state="expanded")
st.markdown("<style>[data-testid='stSidebarNav']{display:none}</style>", unsafe_allow_html=True)

if "token" not in st.session_state:
    st.switch_page("home.py")
token = st.session_state["token"]

title_col, logout_col = st.columns([10, 2])
title_col.title("💬 Adapt-RAG Chat")
if logout_col.button("🔒 Logout", use_container_width=True):
    st.session_state.clear()
    st.switch_page("home.py")

with st.sidebar:
    st.header("📂 Upload Documents")
    st.caption(f"Signed in as **{st.session_state['username']}**. Your documents are private to you.")
    uploaded_file = st.file_uploader("PDF or TXT (max 20 MB)", type=["pdf", "txt"])
    description = st.text_input(
        "Describe the document",
        max_chars=300,
        placeholder="E.g. LangGraph tutorial with workflows and code examples",
    )
    if st.button("Upload", disabled=not (uploaded_file and description.strip())):
        with st.spinner("Indexing..."):
            data, err = document_upload_rag(uploaded_file, description.strip(), token)
        if err or not data.get("status"):
            st.error(f"Upload failed: {err or 'could not store document'}")
        else:
            st.success(f"Indexed {uploaded_file.name}")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for role, text in st.session_state.chat_history:
    st.chat_message(role).write(text)

if question := st.chat_input("Ask a question..."):
    st.chat_message("user").write(question)
    with st.chat_message("assistant"), st.spinner("Thinking..."):
        data, err = query_backend(question, token)
        answer = data["result"]["content"] if data else f"⚠️ {err}"
        st.write(answer)
    st.session_state.chat_history += [("user", question), ("assistant", answer)]
