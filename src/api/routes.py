"""
API routes for RAG operations.
"""

from fastapi import APIRouter, UploadFile, File, Header
from pydantic import BaseModel
import uuid
from langchain_core.messages import HumanMessage, AIMessage

from src.memory.chat_history_mongo import ChatHistory
from src.models.query_request import QueryRequest
from src.rag.document_upload import documents
from src.rag.graph_builder import builder

router = APIRouter()


@router.post("/rag/query")
async def rag_query(req: QueryRequest):
    """
    Process a RAG query and return the result.

    Args:
        req: The query request containing query text and session_id.

    Returns:
        The generated response from the RAG pipeline.
    """
    #chat_history=ChatInMemoryHistory.get_session_history(req.token)
    chat_history = ChatHistory.get_session_history(req.session_id)
    await chat_history.add_message(HumanMessage(content=req.query))

    # Fetch full history
    messages = await chat_history.get_messages()
    result = builder.invoke({
        "messages": messages
    })
    output_text = result["messages"][-1].content

    # Save assistant message
    await chat_history.add_message(AIMessage(content=output_text))

    return {"result": result["messages"][-1]}


@router.post("/rag/documents/upload")
async def upload_file(
    file: UploadFile = File(...),
    description: str = Header(..., alias="X-Description")
):
    """
    Upload a document for RAG processing.

    Args:
        file: The file to upload (PDF or TXT).
        description: Document description provided via header.

    Returns:
        Upload status.
    """
    status_upload = documents(description, file)
    return {"status": status_upload}


class UserAuth(BaseModel):
    username: str
    password: str

@router.post("/api/init")
async def init_session():
    """Initialize a session and return an API token."""
    return {"api_token": str(uuid.uuid4())}

@router.post("/api/create_user")
async def api_create_user(user: UserAuth):
    """Create a new user."""
    # Dummy implementation for now
    return {"status": "success"}

@router.post("/api/login")
async def api_login(user: UserAuth):
    """Log in a user."""
    # Dummy implementation for now
    return {"jwt": str(uuid.uuid4())}
