"""Indexa documentos (PDF, MD, TXT) en la DB vectorial.

Uso: uv run rag-ingest [directorio]   (por defecto: data/docs)
"""

import sys
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from multi_agent.rag.vectorstore import get_vectorstore

LOADERS = {".pdf": PyPDFLoader, ".md": TextLoader, ".txt": TextLoader}


def load_documents(root: Path):
    docs = []
    for path in sorted(root.rglob("*")):
        loader_cls = LOADERS.get(path.suffix.lower())
        if loader_cls:
            docs.extend(loader_cls(str(path)).load())
    return docs


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "data/docs")
    docs = load_documents(root)
    if not docs:
        print(f"No hay documentos en {root}")
        return
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(docs)
    get_vectorstore().add_documents(chunks)
    print(f"Indexados {len(chunks)} fragmentos de {len(docs)} documentos desde {root}")


if __name__ == "__main__":
    main()
