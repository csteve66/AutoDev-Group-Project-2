from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.text_splitter import SemanticChunker
from langchain_ollama import ChatOllama
from mcp.server.fastmcp import FastMCP

APP_ROOT = Path.cwd()
DOCS_DIR = APP_ROOT / "docs"
VECTOR_DIR = APP_ROOT / ".autodev_vectorstore"
EMBEDDING_MODEL = os.getenv("AUTODEV_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
GEN_MODEL = os.getenv("AUTODEV_MODEL", "llama3.1")

mcp = FastMCP("autodev-rag")
embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)


def _vectordb() -> Chroma:
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name="autodev_docs",
        embedding_function=embeddings,
        persist_directory=str(VECTOR_DIR),
    )


@mcp.tool()
def ingest_docs(path: Optional[str] = None) -> str:
    """
    Ingest local docs using semantic chunking and persist vectors.
    """
    target = Path(path) if path else DOCS_DIR
    if not target.exists():
        return f"Docs path does not exist: {target}"

    loader = DirectoryLoader(
        str(target),
        glob="**/*.*",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    docs = loader.load()
    if not docs:
        return "No documents found to ingest."

    splitter = SemanticChunker(embeddings)
    split_docs = splitter.split_documents(docs)
    db = _vectordb()
    db.add_documents(split_docs)
    return f"Ingested {len(split_docs)} semantic chunks from {len(docs)} files."


@mcp.tool()
def query_docs_hyde(query: str, k: int = 5) -> str:
    """
    Retrieve relevant docs with HyDE: generate hypothetical answer,
    retrieve by that synthetic text, then return top chunks.
    """
    db = _vectordb()
    hyde_prompt = ChatPromptTemplate.from_template(
        "Write a concise technical passage that would answer this question:\n{query}\n"
    )
    try:
        llm = ChatOllama(model=GEN_MODEL, temperature=0)
        synthetic = llm.invoke(hyde_prompt.format_messages(query=query)).content
    except Exception:  # noqa: BLE001
        # Fallback if Ollama or model is unavailable: use query directly.
        synthetic = query
    retriever = db.as_retriever(search_kwargs={"k": k})
    docs: list[Document] = retriever.invoke(str(synthetic))

    if not docs:
        return "No relevant chunks found."

    rendered = []
    for idx, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        rendered.append(f"[{idx}] source={source}\n{doc.page_content[:1200]}")
    return "\n\n".join(rendered)


if __name__ == "__main__":
    mcp.run()
