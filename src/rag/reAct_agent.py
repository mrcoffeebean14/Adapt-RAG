from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from src.config.settings import Config
from src.llms.openai import llm
from src.rag.retriever_setup import get_retriever_tool

config = Config()


def get_agent_executor() -> AgentExecutor:
    tools = [get_retriever_tool()]
    prompt = PromptTemplate.from_template(
        "{system_prompt}\n\n"
        "You have access to the following tools:\n"
        "{tools}\n\n"
        "Use this format:\n"
        "Question: the input question you must answer\n"
        "Thought: think about what to do next\n"
        "Action: the action to take, should be one of [{tool_names}]\n"
        "Action Input: the input to the action\n"
        "Observation: the result of the action\n"
        "... (this Thought/Action/Action Input/Observation can repeat)\n"
        "Thought: I now know the final answer\n"
        "Final Answer: the final answer to the original input question\n\n"
        "Question: {input}\n"
        "Thought:{agent_scratchpad}"
    ).partial(system_prompt=config.prompt("system_prompt"))
    react_agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=react_agent,
        tools=tools,
        handle_parsing_errors=True,
        max_iterations=2,
        verbose=True,
        return_intermediate_steps=True,
    )
