"""
HTTP client for the FastAPI backend. Every call returns (data, error):
exactly one is None.
"""

import os

import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
TIMEOUT = 180  # a query can chain several LLM calls


def _post(path: str, token: str | None = None, **kwargs):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.post(f"{BACKEND_URL}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
    except requests.RequestException as e:
        return None, f"Backend unreachable: {e}"
    if r.ok:
        return r.json(), None
    try:
        detail = r.json().get("detail", r.text)
    except ValueError:
        detail = r.text
    if isinstance(detail, list):  # FastAPI validation errors
        detail = "; ".join(f"{e['loc'][-1]}: {e['msg']}" for e in detail)
    return None, f"{r.status_code}: {detail}"


def create_user(username: str, password: str):
    return _post("/api/create_user", json={"username": username, "password": password})


def login_user(username: str, password: str):
    return _post("/api/login", json={"username": username, "password": password})


def query_backend(query: str, token: str):
    return _post("/rag/query", token, json={"query": query})


def document_upload_rag(file, description: str, token: str):
    return _post(
        "/rag/documents/upload",
        token,
        files={"file": (file.name, file.getvalue(), file.type)},
        data={"description": description},
    )
