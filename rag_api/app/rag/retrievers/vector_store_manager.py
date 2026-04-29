# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from pathlib import Path
import yaml
from typing import List, Optional
from langchain_core.documents import Document
from langchain_chroma import Chroma

from rag.document_processing.document_loader import DocumentLoaderFactory
from rag.document_processing.text_splitter import DocumentSplitter
from rag.document_processing.embeddings_manager import EmbeddingsManager

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manage vector stores: KB and temporary ones for evaluation (LangChain + Chroma)."""

    def __init__(self):
        """Initialize the vector store manager."""

        # Load config anchored to project root (src/)
        project_root = Path(__file__).resolve().parents[2]
        config_path = project_root / "config" / "config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f) or {}

        configured = Path(self.cfg.get("vector_store", {}).get("path", "data/vector_store"))

        # If configured path is relative, resolve it against project_root
        if not configured.is_absolute():
            self.vs_path = (project_root / configured).resolve()
        else:
            self.vs_path = configured.resolve()

        # Embeddings & splitter
        self.embeddings = EmbeddingsManager().get_langchain_embeddings()
        self.splitter = DocumentSplitter()

        logger.info(f"VectorStoreManager initialized. Store path: {self.vs_path}")

        # Store reference (set after build or load)
        self.vector_store: Optional[Chroma] = None

    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """Load and split documents using your DocumentLoaderFactory and DocumentSplitter."""

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

    def build_vector_store(self, documents: List[Document], persist: bool = True, path: Optional[Path] = None) -> Chroma:
        """
        Create a vector store. If persist=False, it's temporary in memory.
        Stores returned object in self.vector_store for subsequent retrievals.
        """

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

    def load_vector_store(self, path: Optional[Path] = None):
        """Load an existing persisted vector store (KB)."""

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

    def create_retriever(self, vector_store: Optional[Chroma] = None, search_type: str = "mmr", **kwargs):
        """Return a retriever for the given vector store."""

        store = vector_store or self.vector_store
        if store is None:
            logger.error("create_retriever called but no vector store is loaded or built")
            raise ValueError("Vector store not loaded or built")
        return store.as_retriever(search_type=search_type, **kwargs)

    def retrieve(self, query: str, k: int = 30) -> List[Document]:
        """
        Retrieve up to k relevant documents, using MMR with high fetch_k to maximize results.
        - Returns exactly k if possible.
        - If fewer chunks exist, returns all available chunks.
        """
        
        if self.vector_store is None:
            logger.error("retrieve() called but vector store is not loaded or built")
            raise RuntimeError("Vector store not loaded or built.")

        collection_size = self.vector_store._collection.count()
        retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={'k': k, 'fetch_k': min(max(k * 5, 50), collection_size)}
        )

        results = retriever.invoke(query) or []
        logger.debug(f"Retrieved {len(results[:k])}/{k} chunks for query: '{query[:60]}...'")
        return results[:k]
