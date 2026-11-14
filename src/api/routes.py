"""
API routes: auth, RAG query, document upload.
"""

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from src.api.auth import hash_password, make_token, user_from_token, verify_password
from src.db.mongo_client import db
from src.memory.chat_history_mongo import MongoDBChatMessageHistory
from src.models.query_request import QueryRequest
from src.rag.document_upload import documents
from src.rag.graph_builder import builder

router = APIRouter()
users = db["users"]


def current_user(authorization: str = Header("")) -> str:
    """Resolve `Authorization: Bearer <token>` to a username, or 401."""
    user = user_from_token(authorization.removeprefix("Bearer ").strip())
    if not user:
        raise HTTPException(401, "Invalid or missing token. Log in again.")
    return user


@router.post("/rag/query")
async def rag_query(req: QueryRequest, user: str = Depends(current_user)):
    """Run the question through the graph with the user's recent history."""
    history = MongoDBChatMessageHistory(user)
    await history.add_message(HumanMessage(content=req.query))
    messages = await history.get_messages()

    # ainvoke runs the sync nodes in a thread pool instead of blocking the event loop.
    result = await builder.ainvoke({"messages": messages, "user": user})
    answer = result["messages"][-1].content

    await history.add_message(AIMessage(content=answer))
    return {"result": {"type": "ai", "content": answer}}


@router.post("/rag/documents/upload")
def upload_file(
    file: UploadFile = File(...),
    description: str = Form(..., min_length=1, max_length=300),
    user: str = Depends(current_user),
):
    """Index a PDF/TXT for the current user. Sync def: FastAPI runs it in a thread pool."""
    return {"status": documents(description, file, user)}


class UserAuth(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


@router.post("/api/create_user")
async def api_create_user(user: UserAuth):
    try:
        # _id = username: Mongo enforces uniqueness for us.
        await users.insert_one({"_id": user.username, "password": hash_password(user.password)})
    except DuplicateKeyError:
        raise HTTPException(409, "Username already taken")
    return {"status": "success"}


@router.post("/api/login")
async def api_login(user: UserAuth):
    doc = await users.find_one({"_id": user.username})
    if not doc or not verify_password(user.password, doc["password"]):
        raise HTTPException(401, "Invalid username or password")
    return {"token": make_token(user.username)}
