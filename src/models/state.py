"""
State model for the graph-based RAG system.
"""

from typing import TypedDict, Annotated, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


class State(TypedDict, total=False):
    """State schema for the RAG graph."""

    messages: Annotated[list[AnyMessage], add_messages]
    user: str  # owner whose documents may be retrieved
    binary_score: Optional[str]
    route: Optional[str]
    latest_query: Optional[str]
    rewrite_attempts: int
