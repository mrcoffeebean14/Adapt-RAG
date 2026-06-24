import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
if not groq_api_key:
    raise RuntimeError("GROQ_API_KEY is not set. Add it to your environment or .env file.")

os.environ["GROQ_API_KEY"] = groq_api_key
llm = ChatGroq(model="llama-3.3-70b-versatile")
