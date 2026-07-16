#!/usr/bin/env bash
# Hugging Face Spaces entrypoint: run the FastAPI backend (internal :8000) and
# the Streamlit frontend (public :7860) in one container. The frontend talks to
# the backend over localhost, so BACKEND_URL's default is correct.
set -e

.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# Wait for the backend (torch import takes a while) before serving the UI.
until .venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" 2>/dev/null; do
  echo "waiting for backend..."
  sleep 2
done

exec .venv/bin/streamlit run streamlit_app/home.py \
  --server.address=0.0.0.0 \
  --server.port=7860 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false
