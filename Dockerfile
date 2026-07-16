# Shared image for the FastAPI backend and the Streamlit frontend.
# One pyproject.toml -> one dependency install; the two services differ only by
# their command (set in docker-compose.yml).
FROM python:3.11-slim

# uv for dependency management (matches the local workflow)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Bake the embedding model into the image so the container doesn't download it
# on the first request (~90MB, all-MiniLM-L6-v2).
RUN .venv/bin/python -c "from langchain_community.embeddings import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')"

COPY . .

# Default command runs BOTH services (for Hugging Face Spaces, which exposes one
# port): Streamlit on 7860, backend internal on 8000. docker-compose.yml overrides
# this per-service, so this default only affects single-container deploys like HF.
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh
EXPOSE 7860
CMD ["./start.sh"]
