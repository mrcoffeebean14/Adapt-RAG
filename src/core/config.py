import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

settings = Settings()

# Set env variables for LangChain integrations
os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY