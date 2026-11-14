"""
Shared Groq LLM. Reads GROQ_API_KEY from the environment.
"""

import os

from langchain_groq import ChatGroq

import src.core.config  # noqa: F401  (loads .env)

# Groq retires models often; override with GROQ_MODEL instead of editing code.
# temperature=0: routing/grading need repeatable answers.
llm = ChatGroq(model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), temperature=0)
