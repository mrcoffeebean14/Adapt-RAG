"""
Graph builder module for the adaptive RAG system.
"""

from datetime import date

from langchain_community.tools import TavilySearchResults
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langgraph.constants import START, END
from langgraph.graph.state import StateGraph

from src.config.settings import Config
from src.llms.groq import llm
from src.models.grade import Grade
from src.models.route_identifier import RouteIdentifier
from src.models.state import State
from src.rag.retriever_setup import retrieve
from src.tools.graph_tools import routing_tool, doc_tool

config = Config()


def _prompt(key: str):
    return PromptTemplate.from_template(config.prompt(key))


def _today() -> str:
    """The model has no clock; without this it presents old web results as today's."""
    return date.today().strftime("%B %d, %Y")


def _user_question(state: State) -> str:
    """The user's original wording (latest_query may have been rewritten)."""
    return next(m.content for m in reversed(state["messages"]) if m.type == "human")


def query_classifier(state: State):
    """Label the question index / general / search, using the user's docs as evidence."""
    question = state["messages"][-1].content
    context = retrieve(question, state["user"])
    # Lets it spot questions about the chat itself, which only general_llm can answer.
    history = "\n".join(f"{m.type}: {m.content[:300]}" for m in state["messages"][-7:-1])
    result = (_prompt("classify_prompt") | llm.with_structured_output(RouteIdentifier, method="json_schema")).invoke(
        {"question": question, "context": context or "(no documents)", "history": history or "(none)"}
    )
    print(f"[query_analysis] route={result.route}")
    return {"route": result.route, "latest_query": question, "rewrite_attempts": 0}


def general_llm(state: State):
    """Answer from the model's own knowledge, with chat history."""
    # Without instructions, a long last answer made "summarise our chat" cover only that answer.
    system = SystemMessage(content=config.prompt("general_prompt").format(today=_today()))
    return {"messages": llm.invoke([system, *state["messages"]])}


def retriever_node(state: State):
    """Fetch the user's chunks for the (possibly rewritten) query."""
    content = retrieve(state["latest_query"], state["user"])
    return {"messages": [AIMessage(content=content)]}


def grade(state: State):
    """Judge whether the retrieved context is relevant to the query."""
    result = (_prompt("grading_prompt") | llm.with_structured_output(Grade, method="json_schema")).invoke(
        {"question": state["latest_query"], "context": state["messages"][-1].content}
    )
    print(f"[grade] {result.binary_score}")
    return {"binary_score": result.binary_score}


def rewrite_query(state: State):
    """Rephrase the query for better retrieval; counts toward MAX_REWRITES."""
    result = (_prompt("rewrite_prompt") | llm).invoke({"query": state["latest_query"]})
    return {
        "latest_query": result.content,
        "rewrite_attempts": state.get("rewrite_attempts", 0) + 1,
    }


def generate(state: State):
    """Answer the user's question from the last message's context."""
    result = (_prompt("generate_prompt") | llm).invoke(
        {"question": _user_question(state), "context": state["messages"][-1].content, "today": _today()}
    )
    return {"messages": [AIMessage(content=result.content)]}


def web_search(state: State):
    """Search the web with Tavily and pass the snippets on as context."""
    # The date steers Tavily to recent pages ("latest X" alone returned months-old articles).
    result = TavilySearchResults(max_results=5).invoke(f"{state['latest_query']} as of {_today()}")
    # Tavily returns an error string instead of raising; treat it as no results.
    # The URL often carries the event/date (".../2026-mexican-grand-prix"), which helps pick the latest.
    contents = [
        f"Source: {item.get('url', 'unknown')}\n{item['content']}"
        for item in result if isinstance(item, dict) and "content" in item
    ]
    return {"messages": [AIMessage(content="\n\n".join(contents))]}


graph = StateGraph(State)

graph.add_node("query_analysis", query_classifier)
graph.add_node("retriever", retriever_node)
graph.add_node("grade", grade)
graph.add_node("generate", generate)
graph.add_node("rewrite", rewrite_query)
graph.add_node("web_search", web_search)
graph.add_node("general_llm", general_llm)

graph.add_edge(START, "query_analysis")
graph.add_conditional_edges("query_analysis", routing_tool)
graph.add_edge("retriever", "grade")
graph.add_conditional_edges("grade", doc_tool)
graph.add_edge("rewrite", "retriever")
graph.add_edge("web_search", "generate")
graph.add_edge("generate", END)
graph.add_edge("general_llm", END)

builder = graph.compile()
