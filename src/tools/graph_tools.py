"""
Conditional-edge functions for the RAG graph.
"""

from typing import Literal

from src.models.state import State

# Max rewrite→retrieve retries before answering with what we have.
MAX_REWRITES = 2


def routing_tool(state: State) -> Literal["retriever", "general_llm", "web_search"]:
    """Route by the classifier's label; anything unrecognised goes to web search."""
    route = (state.get("route") or "").strip().lower()
    return {"index": "retriever", "general": "general_llm"}.get(route, "web_search")


def doc_tool(state: State) -> Literal["rewrite", "generate"]:
    """Generate if the context was graded relevant or the retry budget is spent."""
    relevant = (state.get("binary_score") or "").strip().lower().startswith("yes")
    if relevant or state.get("rewrite_attempts", 0) >= MAX_REWRITES:
        return "generate"
    return "rewrite"


if __name__ == "__main__":
    assert routing_tool({"route": " Index "}) == "retriever"
    assert routing_tool({"route": "general"}) == "general_llm"
    assert routing_tool({"route": None}) == "web_search"
    assert doc_tool({"binary_score": "Yes."}) == "generate"
    assert doc_tool({"binary_score": "no"}) == "rewrite"
    assert doc_tool({"binary_score": "no", "rewrite_attempts": MAX_REWRITES}) == "generate"
    print("graph_tools ok")
