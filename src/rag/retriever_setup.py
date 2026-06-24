from langchain_community.document_loaders import WebBaseLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.tools import create_retriever_tool
from functools import lru_cache

DEFAULT_TOP_K = 4

urls = [
    "https://langchain-ai.github.io/langgraph/concepts/why-langgraph/",
    "https://langchain-ai.github.io/langgraph/tutorials/workflows/",
    "https://langchain-ai.github.io/langgraph/how-tos/graph-api/#map-reduce-and-the-send-api"
]


def _build_vector_store() -> FAISS:
    loader = WebBaseLoader(urls)
    docs = loader.load()
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    ).split_documents(docs)

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return FAISS.from_documents(chunks, embeddings)


@lru_cache(maxsize=1)
def get_retriever():
    vector_store = _build_vector_store()
    return vector_store.as_retriever(search_kwargs={"k": DEFAULT_TOP_K})


@lru_cache(maxsize=1)
def get_retriever_tool():
    retriever = get_retriever()
    return create_retriever_tool(
        retriever,
        "retriever_vectorstore_langgraph",
        (
            "Use this tool only to answer questions about LangGraph documentation. "
            "Do not use this tool for anything else."
        )
    )
