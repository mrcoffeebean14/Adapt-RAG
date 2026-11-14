"""
Document upload: validate, load, chunk, tag with owner, store.
"""

import os
import tempfile

from fastapi import HTTPException, UploadFile
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.rag.retriever_setup import retriever_chain

MAX_BYTES = 20 * 1024 * 1024
LOADERS = {".pdf": PyPDFLoader, ".txt": lambda p: TextLoader(p, encoding="utf-8")}


def documents(description: str, file: UploadFile, user: str) -> bool:
    """Index an uploaded PDF/TXT for `user`. Raises HTTPException on bad input."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in LOADERS:
        raise HTTPException(400, "Only PDF and TXT files are supported")

    file_bytes = file.file.read(MAX_BYTES + 1)
    if len(file_bytes) > MAX_BYTES:
        raise HTTPException(413, "File larger than 20 MB")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name
    try:
        docs = LOADERS[ext](tmp_path).load()
    except Exception as e:
        raise HTTPException(400, f"Could not read file: {e}")
    finally:
        os.unlink(tmp_path)

    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150).split_documents(docs)
    if not chunks:
        raise HTTPException(400, "No extractable text (scanned PDFs need OCR first)")
    for chunk in chunks:
        chunk.metadata.update(user=user, description=description, source=file.filename)

    return retriever_chain(chunks)
