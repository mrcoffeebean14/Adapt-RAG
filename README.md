---
title: Adapt RAG
emoji: 💬
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: 6.32.0
python_version: "3.11"
app_file: app.py
pinned: false
---

# Adapt-RAG

An adaptive RAG chatbot. Each question is routed by an LLM to the best source:

- **index**: your uploaded documents (Qdrant), with relevance grading and query rewriting
- **general**: the LLM's own knowledge, with your chat history
- **search**: live web search (Tavily)

FastAPI + LangGraph backend with a Gradio UI (one process, port 7860), Groq LLM, MongoDB for users and chat history.
Each user's documents and history are private to them.

```
START → query_analysis ─ index   → retriever → grade ─ relevant ──────────────→ generate → END
                       │                          └ not relevant → rewrite → retriever (max 2 rewrites)
                       ├ general → general_llm → END
                       └ search  → web_search → generate → END
```

## Run locally

```bash
uv sync
cp .env.example .env          # fill in GROQ_API_KEY, TAVILY_API_KEY, SECRET_KEY
```

**Without Docker** (needs Mongo and Qdrant, local or cloud, set in `.env`):

```bash
uv run python app.py          # UI http://localhost:7860 · API docs http://localhost:7860/docs
```

**Everything in Docker** (also starts Mongo + Qdrant):

```bash
docker compose up --build     # same URLs
```

Self-checks for the auth and routing logic: `uv run python -m src.api.auth` and `uv run python -m src.tools.graph_tools`.

## Deploy to Hugging Face Spaces (free, Gradio SDK)

The settings at the top of this README make the repo a **Gradio** Space (Docker Spaces are paid).
Hugging Face installs [requirements.txt](requirements.txt) with pip and runs `python app.py`.
The databases have to be hosted services, because a Space's disk is wiped on restart.
`requirements.txt` is generated from `uv.lock` (the command is in its header). Regenerate it
whenever dependencies change, and keep `sdk_version` equal to the pinned `gradio` version.

1. **MongoDB Atlas**: create a free M0 cluster at https://cloud.mongodb.com.
   - Database Access → add a user.
   - Network Access → allow `0.0.0.0/0` (Spaces have no fixed IP).
   - Connect → Drivers → copy the `mongodb+srv://…` URL and put the password in it.
2. **Qdrant Cloud**: create a free cluster at https://cloud.qdrant.io and copy its URL and API key.
3. **Keys**: get a Groq key at https://console.groq.com and a Tavily key at https://app.tavily.com.
   Generate a secret with `python -c "import secrets; print(secrets.token_hex(32))"`.
4. **Space → Settings → Variables and secrets**: add these as *secrets*. Paste the raw value
   **without quotes**: a quoted value copied from `.env` is sent to the provider as-is, and Groq
   then answers `401 Invalid API Key`.

   | Name | Value |
   |---|---|
   | `GROQ_API_KEY` | Groq key |
   | `TAVILY_API_KEY` | Tavily key |
   | `SECRET_KEY` | the generated secret, at least 32 characters; the app refuses to start with a shorter one (if it changes, everyone is logged out) |
   | `MONGODB_URL` | Atlas `mongodb+srv://…` URL |
   | `QDRANT_URL` | Qdrant Cloud URL (`https://…:6333`) |
   | `QDRANT_API_KEY` | Qdrant Cloud key |
   | `MONGODB_DB_NAME` *(optional)* | defaults to `adaptive_rag`; must match what you use locally if you want to share data |
   | `GROQ_MODEL` *(optional)* | defaults to `openai/gpt-oss-120b` |

5. **Create the Space**: huggingface.co/new-space, choose SDK **Gradio**, Blank template, **CPU basic**.
6. **Push** the `deployment` branch to the Space's `main` (Spaces only build `main`):
   `git push --force space deployment:main`. The force replaces the template commit the Space
   was created with. The first boot downloads the embedding model, which takes about 30 s.
7. **Check it**: open the Space, create an account, upload a small `.txt`, and ask about it.
   Build and runtime logs are on the Space's **Logs** tab.

**Any VPS instead:** install Docker, copy the repo and a filled-in `.env`, then run
`docker compose up --build -d`. Put a reverse proxy with HTTPS (e.g. Caddy) in front of port 7860.

## API

All `/rag/*` endpoints need `Authorization: Bearer <token>` from `/api/login`.

| Endpoint | Body | Returns |
|---|---|---|
| `POST /api/create_user` | `{"username", "password"}` (username 3–40 chars `[A-Za-z0-9_.-]`, password ≥ 8) | `200`, or `409` if the username is taken |
| `POST /api/login` | `{"username", "password"}` | `{"token": "..."}`, or `401` |
| `POST /rag/query` | `{"query": "..."}` | `{"result": {"type": "ai", "content": "..."}}` |
| `POST /rag/documents/upload` | multipart: `file` (PDF/TXT ≤ 20 MB), `description` | `{"status": true}` |

```bash
curl -X POST localhost:7860/api/create_user -H 'Content-Type: application/json' -d '{"username":"me","password":"password123"}'
TOKEN=$(curl -s -X POST localhost:7860/api/login -H 'Content-Type: application/json' -d '{"username":"me","password":"password123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -X POST localhost:7860/rag/documents/upload -H "Authorization: Bearer $TOKEN" -F file=@notes.pdf -F description="My notes"
curl -X POST localhost:7860/rag/query -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"query":"Summarise my notes"}'
```

## Layout

```
src/main.py                 FastAPI app (+ Mongo index on startup, /health)
src/api/routes.py           endpoints
src/api/auth.py             scrypt password hashes, HMAC-signed tokens (stdlib)
src/rag/graph_builder.py    LangGraph nodes and wiring
src/tools/graph_tools.py    conditional edges (routing, rewrite limit)
src/rag/retriever_setup.py  Qdrant store, per-user retrieval
src/rag/document_upload.py  validate → load → chunk → store
src/memory/chat_history_mongo.py  chat history (last 20 messages go to the LLM)
src/config/prompts.yaml     all prompts
app.py                      entry point: mounts the Gradio UI on the FastAPI app
requirements.txt            pip pins for Hugging Face (generated from uv.lock)
```

## Known limits

- Login tokens expire after 7 days and can't be revoked early. Rotating `SECRET_KEY` logs everyone out.
- 5 failed logins lock that account for the rest of a 15-minute window. Anyone who knows a username can trigger this. There is no per-IP limit.
- Sign-up is open, so anyone who signs up uses your Groq and Tavily quota. Add rate limiting before you share the Space widely.
- Scanned PDFs (images only) have no text to index.
