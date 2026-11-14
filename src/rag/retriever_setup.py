"""
Qdrant-backed document store. Each chunk carries metadata.user, and every
search is filtered to the caller's own documents.
"""

from functools import cache

from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance, FieldCondition, Filter, MatchValue, PayloadSchemaType, VectorParams,
)

from src.core.config import settings

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

COLLECTION = settings.DOCS_COLLECTION
# Construction doesn't connect; a bad URL surfaces on the first collection op.
_client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)


@cache
def _vectorstore() -> QdrantVectorStore:
    """Connect once, creating the collection and the user index on first use."""
    if not _client.collection_exists(COLLECTION):
        dim = len(embeddings.embed_query("dimension probe"))
        _client.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    # Idempotent. Qdrant Cloud refuses filters on unindexed fields.
    _client.create_payload_index(COLLECTION, "metadata.user", PayloadSchemaType.KEYWORD)
    return QdrantVectorStore(client=_client, collection_name=COLLECTION, embedding=embeddings)


def retriever_chain(chunks: list[Document]) -> bool:
    """Store document chunks. Returns True on success."""
    try:
        _vectorstore().add_documents(chunks)
        print(f"Stored {len(chunks)} chunks in Qdrant collection '{COLLECTION}'")
        return True
    except Exception as e:
        print(f"Error storing documents in Qdrant: {e}")
        return False


def retrieve(query: str, user: str, k: int = 4) -> str:
    """Top-k chunks from this user's documents as plain text ("" if none)."""
    own_docs = Filter(must=[FieldCondition(key="metadata.user", match=MatchValue(value=user))])
    docs = _vectorstore().similarity_search(query, k=k, filter=own_docs)
    return "\n\n".join(d.page_content for d in docs)
