"""
Retriever setup and vector store configuration (Qdrant-backed).

Documents live in a persistent Qdrant collection, so they survive restarts and
are shared across backend replicas (unlike the old in-memory FAISS global).
"""

import os

from langchain_core.documents import Document
from langchain_core.tools import create_retriever_tool
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from src.core.config import settings

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

COLLECTION = settings.DOCS_COLLECTION
# Client construction is lazy about connecting, so import stays safe even if
# Qdrant is down; the first collection op is where a bad URL would surface.
_client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)


def _vectorstore() -> QdrantVectorStore:
    """Connect to the Qdrant collection, creating it on first use."""
    if not _client.collection_exists(COLLECTION):
        dim = len(embeddings.embed_query("dimension probe"))
        _client.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    return QdrantVectorStore(
        client=_client,
        collection_name=COLLECTION,
        embedding=embeddings,
    )


def retriever_chain(chunks: list[Document]):
    """
    Store document chunks in the Qdrant collection.

    Args:
        chunks: List of document chunks to store.

    Returns:
        Boolean indicating success of the operation.
    """
    try:
        _vectorstore().add_documents(chunks)
        print(f"Stored {len(chunks)} chunks in Qdrant collection '{COLLECTION}'")
        return True
    except Exception as e:
        print(f"Error storing documents in Qdrant: {e}")
        return False


def get_retriever():
    """
    Get a retriever tool over the persistent Qdrant collection.

    An empty collection simply returns no results, so no cold-start dummy is
    needed. The tool description is loaded from description.txt (rewritten on
    each upload).

    Returns:
        A LangChain retriever tool configured for the vector store.
    """
    retriever = _vectorstore().as_retriever()

    description = None
    if os.path.exists("description.txt"):
        with open("description.txt", "r", encoding="utf-8") as f:
            description = f.read()

    return create_retriever_tool(
        retriever,
        "retriever_customer_uploaded_documents",
        f"Use this tool **only** to answer questions about: {description}\n"
        "Don't use this tool to answer anything else.",
    )
