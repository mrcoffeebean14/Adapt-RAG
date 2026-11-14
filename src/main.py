"""
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import router
from src.memory.chat_history_mongo import collection as chat_history


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent; keeps per-user history lookups fast as the collection grows.
    await chat_history.create_index([("session_id", 1), ("timestamp", -1)])
    yield


app = FastAPI(title="Adaptive RAG API", lifespan=lifespan)
app.include_router(router)


@app.get("/health")  # "/" belongs to the Gradio UI (see app.py)
async def health():
    """Health check."""
    return {"message": "Adaptive RAG API is running"}
