# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from pathlib import Path
from typing import List, Optional

import yaml
from langchain_chroma import Chroma
from langchain_core.documents import Document

from rag.document_processing import DocumentLoaderFactory, DocumentSplitter
from .embeddings import EmbeddingsManager

logger = logging.getLogger(__name__)


class VectorStore:
    """Chroma vector store: build, persist, load, and extract docs."""

    def __init__(self):
        project_root = Path(__file__).resolve().parents[3]
        config_path = project_root / "config" / "config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f) or {}

        configured = Path(self.cfg.get("vector_store", {}).get("path", "data/vector_store"))
        if not configured.is_absolute():
            self.vs_path = (project_root / configured).resolve()
        else:
            self.vs_path = configured.resolve()

        self.embeddings = EmbeddingsManager().get_langchain_embeddings()
        self.splitter = DocumentSplitter()

        logger.info(f"VectorStore initialized. Store path: {self.vs_path}")
        self.vector_store: Optional[Chroma] = None

    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """Load and split documents via DocumentLoaderFactory + DocumentSplitter."""

        logger.info(f"Loading {len(file_paths)} file(s) into document chunks")
        all_chunks: List[Document] = []
        for path in file_paths:
            loader = DocumentLoaderFactory.create_loader(path)
            docs = loader.load_document(path)
            for doc in docs:
                chunks = self.splitter.split_content(doc.page_content, doc.metadata)
                all_chunks.extend(chunks)
        logger.info(f"Produced {len(all_chunks)} chunks from {len(file_paths)} file(s)")
        return all_chunks

    def build(self, documents: List[Document], persist: bool = True, path: Optional[Path] = None) -> Chroma:
        """Create a Chroma store. persist=False keeps it in memory only."""

        store_path = path or self.vs_path
        if persist:
            logger.info(f"Building persistent vector store ({len(documents)} docs) at {store_path}")
            if not store_path.exists():
                store_path.mkdir(parents=True, exist_ok=True)
            store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=str(store_path),
            )
            logger.info("Vector store persisted successfully")
        else:
            logger.info(f"Building in-memory vector store ({len(documents)} docs)")
            store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=None,
            )

        self.vector_store = store
        return store

    def load(self, path: Optional[Path] = None) -> Chroma:
        """Load an existing persisted Chroma store."""

        store_path = path or self.vs_path
        if not store_path.exists():
            logger.error(f"Vector store not found at {store_path}")
            raise FileNotFoundError(f"Vector store not found at {store_path}")
        logger.info(f"Loading vector store from {store_path}")
        self.vector_store = Chroma(
            persist_directory=str(store_path),
            embedding_function=self.embeddings,
        )
        return self.vector_store

    def get_docs(self) -> List[Document]:
        """Extract all documents from the loaded Chroma store (for BM25 indexing, etc.)."""

        if self.vector_store is None:
            return []
        data = self.vector_store._collection.get(include=["documents", "metadatas"])
        return [
            Document(page_content=text, metadata=meta or {})
            for text, meta in zip(data.get("documents", []), data.get("metadatas", []))
        ]
