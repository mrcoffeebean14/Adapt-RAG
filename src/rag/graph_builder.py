import pathlib

from langchain_community.tools import TavilySearchResults
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langgraph.constants import START, END
from langgraph.graph.state import StateGraph

from src.rag.reAct_agent import get_agent_executor
from src.rag.retriever_setup import get_retriever
from src.config.settings import Config
from src.llms.openai import llm
from src.models.grade import Grade
from src.models.route_identifier import RouteIdentifier
from src.models.state import State
from src.tools.graph_tools import routing_tool, doc_tool, verify_answer

config = Config()


# Node implementations
def query_classifier(state: State):
    """This is the node to classify the query if it is related to index or not
    Args:
        state (State): the current state of the graph
    """
    question = state["messages"][-1].content
    context = ""
    try:
        top_docs = get_retriever().invoke(question)
        context = "\n\n".join([doc.page_content for doc in top_docs])
    except Exception:
        context = ""

    llm_with_structured_output = llm.with_structured_output(RouteIdentifier)
    classify_prompt = PromptTemplate(
        template=config.prompt("classify_prompt"),
        input_variables=["question", "context"]
    )
    chain = classify_prompt | llm_with_structured_output
    result = chain.invoke({"question": question, "context": context})
    return {
        "messages": state["messages"],
        "route": result.route,
        "latest_query": question,
        "retrieved_context": context,
    }

def general_llm(state: State):
    """This nodes fetches general common knowledge result from the llm
    Args:
        state (State): the current state of the graph
    """
    result = llm.invoke(state["messages"])
    return {"messages": [result]}


def retriever_node(state: State):
    """This node will be used to retriever the result from the vectorStores
    Args:
        state (State): the current state of the graph
    """
    question = state["latest_query"]
    agent_executor = get_agent_executor()
    result = agent_executor.invoke({"input": question})

    intermediate_steps = result.get("intermediate_steps", [])
    tool_calls = []
    retrieved_parts = []
    if intermediate_steps:
        for action, tool_result in intermediate_steps:
            tool_calls.append({
                "tool": action.tool,
                "input": action.tool_input,
            })
            if isinstance(tool_result, str):
                retrieved_parts.append(tool_result)
    new_message = AIMessage(
        content=result["output"],
        additional_kwargs={"tool_calls": tool_calls},
    )
    return {
        "messages": [new_message],
        "retrieved_context": "\n\n".join(retrieved_parts) or state.get("retrieved_context", ""),
    }


def grade(state: State):
    """This node will be used to grade the result from the vectorStores
    Args:
        state (State): the current state of the graph
    """
    grading_prompt = PromptTemplate(
        template=config.prompt("grading_prompt"),
        input_variables=["question", "context"]
    )
    context = state.get("retrieved_context", "") or state["messages"][-1].content
    question = state["latest_query"]

    llm_with_grade = llm.with_structured_output(Grade)

    chain_graded = grading_prompt | llm_with_grade
    result = chain_graded.invoke({"question": question, "context": context})

    return {"messages": state["messages"], "binary_score": result.binary_score}


def rewrite_query(state: State):
    """This node will rewrite the query to get the better results
    Args:
        state (State): State of the question
    """

    query = state["latest_query"]
    rewrite_prompt = PromptTemplate(
        template=config.prompt("rewrite_prompt"),
        input_variables=["query"]
    )
    chain = rewrite_prompt | llm
    result = chain.invoke({"query": query})
    return {
        "latest_query": result.content.strip()
    }


def generate(state: State):
    """This node will generate the answer for the user in the best and suitable way possible.
    Args:
        state (State): State of the question
    """
    context = state.get("retrieved_context", "") or state["messages"][-1].content

    generate_prompt = PromptTemplate(
        template=config.prompt("generate_prompt"),
        input_variables=["question", "context"]
    )

    generate_chain = generate_prompt | llm
    result = generate_chain.invoke({
        "question": state["latest_query"],
        "context": context,
    })

    return {"messages": [AIMessage(content=result.content)]}


def web_search(state: State):
    """This node will search the web for the rewritten query"""

    search_tool = TavilySearchResults()
    result = search_tool.invoke(state["latest_query"])

    contents = [item["content"] for item in result if "content" in item]
    return {
        "messages": [AIMessage(content="\n\n".join(contents))],
        "retrieved_context": "\n\n".join(contents),
    }


graph = StateGraph(State)

graph.add_node("query_analysis", query_classifier)
graph.add_node("retriever", retriever_node)
graph.add_node("grade", grade)
graph.add_node("generate", generate)
graph.add_node("rewrite", rewrite_query)
graph.add_node("web_search", web_search)
graph.add_node("general_llm", general_llm)

graph.add_edge(START, "query_analysis")
graph.add_edge("web_search", "generate")
graph.add_edge("retriever", "grade")
graph.add_edge("rewrite", "retriever")
graph.add_conditional_edges("query_analysis", routing_tool)
graph.add_conditional_edges("grade", doc_tool)
graph.add_conditional_edges("generate", verify_answer)
graph.add_edge("general_llm", END)

builder=graph.compile()


def save_graph_png(output_file: str = "adaptive_RAG.png") -> pathlib.Path:
    png_data = builder.get_graph().draw_mermaid_png()
    output_path = pathlib.Path(output_file)
    output_path.write_bytes(png_data)
    return output_path
