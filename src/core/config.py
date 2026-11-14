"""
Environment settings. load_dotenv() puts .env into os.environ, which is also
where the Groq and Tavily integrations read their API keys from.
"""

import os
import secrets

from dotenv import load_dotenv

load_dotenv()


class Settings:
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
    DOCS_COLLECTION = os.getenv("QDRANT_DOCS_COLLECTION", "documents")
    # Random fallback works, but every restart then logs all users out.
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)


settings = Settings()
