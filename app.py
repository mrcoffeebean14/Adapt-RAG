"""
Entry point: the FastAPI API and a Gradio UI on one port (7860).
Hugging Face Gradio Spaces run `python app.py`; locally it's the same command.

The UI calls the route functions directly (no HTTP hop), so it gets exactly the
API's validation, login limits and per-user document rules.
"""

import os

import gradio as gr
import uvicorn
from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from src.api.routes import UserAuth, api_create_user, api_login, current_user, rag_query
from src.main import app
from src.memory.chat_history_mongo import MongoDBChatMessageHistory
from src.models.query_request import QueryRequest
from src.rag.document_upload import documents


def _error(e: Exception) -> str:
    if isinstance(e, HTTPException):
        return str(e.detail)
    if isinstance(e, ValidationError):
        return "; ".join(f"{err['loc'][-1]}: {err['msg']}" for err in e.errors())
    print(f"[ui] unexpected error: {e!r}")
    return "Something went wrong. Please try again."


async def sign_up(username, password):
    try:
        await api_create_user(UserAuth(username=username, password=password))
        return "✅ Account created. Now log in."
    except Exception as e:
        return f"❌ {_error(e)}"


async def log_in(username, password):
    try:
        token = (await api_login(UserAuth(username=username, password=password)))["token"]
    except Exception as e:
        return {auth_msg: f"❌ {_error(e)}"}
    past = await MongoDBChatMessageHistory(username).get_messages()
    return {
        session: token,
        login_view: gr.Column(visible=False),
        chat_view: gr.Row(visible=True),
        who: f"Signed in as **{username}**. Your documents are private to you.",
        chatbot: [{"role": "user" if m.type == "human" else "assistant", "content": m.content} for m in past],
        auth_msg: "",
        password_box: "",
    }


def log_out():
    return {
        session: None,
        login_view: gr.Column(visible=True),
        chat_view: gr.Row(visible=False),
        chatbot: [],
        file_box: None,
        description_box: "",
        upload_msg: "",
        auth_msg: "",
    }


async def ask(question, history, token):
    question = (question or "").strip()
    if not question:
        yield "", history
        return
    history = history + [{"role": "user", "content": question}]
    yield "", history  # show the question right away
    try:
        user = current_user(f"Bearer {token}")
        answer = (await rag_query(QueryRequest(query=question), user))["result"]["content"]
    except Exception as e:
        answer = f"⚠️ {_error(e)}"
    yield "", history + [{"role": "assistant", "content": answer}]


def upload(path, description, token):
    """Sync on purpose: Gradio runs it in a worker thread while embedding."""
    description = (description or "").strip()
    if not path or not description:
        return "❌ Choose a file and describe it first."
    name = os.path.basename(path)
    try:
        user = current_user(f"Bearer {token}")
        with open(path, "rb") as f:
            ok = documents(description, UploadFile(f, filename=name), user)
        return f"✅ Indexed {name}" if ok else "❌ Could not store the document."
    except Exception as e:
        return f"❌ {_error(e)}"


with gr.Blocks(title="Adapt-RAG") as demo:
    session = gr.State(None)  # login token, held server-side per browser tab

    with gr.Column(visible=True, elem_id="login") as login_view:
        gr.Markdown(
            "# 🔐 Adapt-RAG\n"
            "Ask about your own documents, general knowledge, or the live web."
        )
        username_box = gr.Textbox(label="Username")
        password_box = gr.Textbox(label="Password (min 8 characters)", type="password")
        with gr.Row():
            login_btn = gr.Button("Log in", variant="primary")
            signup_btn = gr.Button("Create account")
        auth_msg = gr.Markdown()

    with gr.Row(visible=False) as chat_view:
        with gr.Column(scale=1, min_width=260):
            who = gr.Markdown()
            file_box = gr.File(label="PDF or TXT (max 20 MB)", file_types=[".pdf", ".txt"], type="filepath")
            description_box = gr.Textbox(
                label="Describe the document",
                max_length=300,
                placeholder="E.g. LangGraph tutorial with workflows and code examples",
            )
            upload_btn = gr.Button("Upload")
            upload_msg = gr.Markdown()
            logout_btn = gr.Button("🔒 Log out")
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="💬 Chat", height=560)
            question_box = gr.Textbox(placeholder="Ask a question...", show_label=False, submit_btn=True)

    login_outputs = [session, login_view, chat_view, who, chatbot, auth_msg, password_box]
    login_btn.click(log_in, [username_box, password_box], login_outputs)
    password_box.submit(log_in, [username_box, password_box], login_outputs)
    signup_btn.click(sign_up, [username_box, password_box], auth_msg)
    upload_btn.click(upload, [file_box, description_box, session], upload_msg)
    question_box.submit(ask, [question_box, chatbot, session], [question_box, chatbot])
    logout_btn.click(
        log_out, None, [session, login_view, chat_view, chatbot, file_box, description_box, upload_msg, auth_msg]
    )

# Gradio runs one call per event at a time by default; let several users chat at once.
demo.queue(default_concurrency_limit=8)

app = gr.mount_gradio_app(
    app,
    demo,
    path="/",
    max_file_size="20mb",
    ssr_mode=False,
    theme=gr.themes.Soft(),
    css="#login { max-width: 480px; margin: 48px auto; }",
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
