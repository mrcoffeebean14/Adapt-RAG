# Self-hosting image (VPS / docker compose / Cloud Run). The Hugging Face Space
# doesn't use this: it runs the Gradio SDK with requirements.txt + app.py.
FROM python:3.11-slim

# uv for dependency management (matches the local workflow)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# The embedding model (~90MB, all-MiniLM-L6-v2) is downloaded on first boot and
# cached to disk, not baked in. Costs ~30s on the very first startup.

COPY . .

# Non-root user with a writable HOME for the embedding-model cache.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user

# One process: FastAPI API + Gradio UI on 7860 (see app.py).
EXPOSE 7860
CMD [".venv/bin/python", "app.py"]
