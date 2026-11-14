"""
Query request model.
"""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for RAG queries."""

    query: str = Field(min_length=1, max_length=4000)
