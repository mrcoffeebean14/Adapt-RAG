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

# The embedding model (~90MB, all-MiniLM-L6-v2) is downloaded on first boot and
# cached to disk, not baked in — keeps the image smaller and builds faster/cheaper
# (matters on HF Spaces' free build quota). Costs ~30s on the very first startup.

COPY . .

# Default command runs BOTH services (for Hugging Face Spaces, which exposes one
# port): Streamlit on 7860, backend internal on 8000. docker-compose.yml overrides
# this per-service, so this default only affects single-container deploys like HF.
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

# HF Spaces runs containers as uid 1000; give it a writable HOME for the
# embedding-model cache.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
EXPOSE 7860
CMD ["./start.sh"]
