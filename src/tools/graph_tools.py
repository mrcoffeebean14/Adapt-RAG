from typing import Literal

from langchain_core.prompts import PromptTemplate

from src.config.settings import Config
from src.llms.openai import llm
from src.models.state import State
from src.models.verification_result import VerificationResult

config = Config()

def routing_tool(state:State) -> Literal["retriever","general_llm","web_search"]:
    """This tool will be used to route the graph to retriever node or web_search node
    Args:
        state (State): the current state of the graph
    """
    if state["route"]=="index":
        return "retriever"
    elif state["route"]=="general":
        return "general_llm"
    else:
        return "web_search"

def doc_tool(state:State) -> Literal["rewrite", "generate", "web_search"]:
    """This is a tool which will be used to determine that if the query needs rewriting or not according to the binary_score"""
    score = state["binary_score"]
    if score == "yes":
        return "generate"
    if not state.get("retrieved_context"):
        return "web_search"
    return "rewrite"

def verify_answer(state:State) -> Literal["__end__","generate"]:
    """Check whether the final answer is faithful to the retrieved context."""
    if state["route"]=="general":
        return "__end__"
    else:
        question = state["latest_query"]
        context = state.get("retrieved_context", "")
        final_answer = state["messages"][-1].content

        verify_prompt = PromptTemplate(
            template=config.prompt("verify_prompt"),
            input_variables=["question", "context", "final_answer"]
        )
        llm_with_verification = llm.with_structured_output(VerificationResult)

        verify_chain = verify_prompt | llm_with_verification

        result = verify_chain.invoke({"question": question, "context": context, "final_answer": final_answer})
        if result.faithful:
            return "__end__"
        return "generate"
