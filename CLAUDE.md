# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                                   # install (uv, not pip)
uv run uvicorn src.main:app --reload --port 8000          # backend  → http://localhost:8000/docs
uv run streamlit run streamlit_app/home.py                # frontend → http://localhost:8501
docker compose up --build                                 # full stack incl. Mongo + Qdrant
uv run python -m src.api.auth                             # self-check: hashing + tokens
uv run python -m src.tools.graph_tools                    # self-check: routing + rewrite limit
```

- No pytest/linter configured. The two `__main__` self-checks above are the only automated checks; they need no network.
- Env vars: see `.env.example`. Required: `GROQ_API_KEY`, `TAVILY_API_KEY`, `SECRET_KEY` (random fallback if unset, which logs everyone out on restart), `MONGODB_URL`, `QDRANT_URL`/`QDRANT_API_KEY`. Optional: `GROQ_MODEL`, `MONGODB_DB_NAME`, `QDRANT_DOCS_COLLECTION`.
- Deployment target is a Hugging Face Docker Space (the git remote `space`); `start.sh` runs both services in one container, with the UI on 7860. See README "Deploy".

## Architecture

Streamlit (`streamlit_app/`) → `utils/api_client.py` (every call returns `(data, error)`) → FastAPI (`src/api/routes.py`) → LangGraph `builder` (`src/rag/graph_builder.py`).

### Auth (`src/api/auth.py`, `routes.py`)
Real but minimal, stdlib only: scrypt password hashes in Mongo `users` (`_id` = username, so Mongo enforces uniqueness), stateless tokens `username.HMAC(SECRET_KEY)`. `current_user` dependency reads `Authorization: Bearer`. Tokens never expire. The username is the key for both chat history and document ownership.

### The graph
```
START → query_analysis (index / general / search)
  ├─ index   → retriever → grade → generate | rewrite → retriever  (loop)
  ├─ general → general_llm → END
  └─ search  → web_search → generate → END
```
- State (`src/models/state.py`) carries `user`; every retrieval is filtered to that user's chunks.
- Loop bound: `rewrite_attempts` (reset in `query_classifier`, incremented in `rewrite_query`) plus `MAX_REWRITES` in `src/tools/graph_tools.py`. Keep it if you touch the loop.
- Structured outputs (`RouteIdentifier`, `Grade`) use `method="json_schema"` with `Literal` fields. gpt-oss on Groq fails the default tool-calling mode ("model did not call a tool").
- `query_classifier` sees the last 6 messages, so questions about the chat itself route to `general`, the only node with full history. Without them, such questions went to web search and the answer was made up.
- `generate` gets the user's original question (last human message) plus the last message as context.
- The route calls `builder.ainvoke`. The nodes are sync, so LangGraph runs them in a thread pool.

### Retrieval (`src/rag/retriever_setup.py`)
Qdrant (persistent) + local `all-MiniLM-L6-v2` embeddings. `_vectorstore()` is `@cache`d and creates the collection and the `metadata.user` keyword index (Qdrant Cloud rejects filters on unindexed fields). `retrieve(query, user)` returns the joined chunk text. Chunks stored before per-user ownership existed have no `metadata.user` and are invisible.

### Chat history (`src/memory/chat_history_mongo.py`)
Mongo `chat_history`, keyed by `session_id` = username. Only the last `HISTORY_WINDOW` (20) messages are loaded into the graph. An index is created in `main.py`'s lifespan.

### Config, two similarly named modules
- `src/config/settings.py::Config`: loads `prompts.yaml` (`classify_prompt`, `grading_prompt`, `rewrite_prompt`, `generate_prompt`).
- `src/core/config.py::Settings`: env vars (calls `load_dotenv`). `src/llms/groq.py` builds the shared `llm` from `GROQ_MODEL`.

`CHANGES.md` (gitignored) is an old debugging log, not a description of current behavior.
