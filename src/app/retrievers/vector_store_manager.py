# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from pathlib import Path
import yaml
from typing import List, Optional
from langchain.schema import Document
from langchain_community.vectorstores import Chroma

from document_processing.document_loader import DocumentLoaderFactory
from document_processing.text_splitter import DocumentSplitter
from document_processing.embeddings_manager import EmbeddingsManager

class VectorStoreManager:
    """Manage vector stores: KB and temporary ones for evaluation (LangChain + Chroma)."""

    def __init__(self):
        """Initialize the vector store manager."""
        # Load config anchored to project root (src/)
        project_root = Path(__file__).resolve().parents[1]
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

        # Store reference (set after build or load)
        self.vector_store: Optional[Chroma] = None

    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """Load and split documents using your DocumentLoaderFactory and DocumentSplitter."""
        all_chunks: List[Document] = []
        for path in file_paths:
            loader = DocumentLoaderFactory.create_loader(path)
            docs = loader.load_document(path)
            for doc in docs:
                chunks = self.splitter.split_content(doc.page_content, doc.metadata)
                all_chunks.extend(chunks)  # splitter returns langchain Documents
        return all_chunks

    def build_vector_store(self, documents: List[Document], persist: bool = True, path: Optional[Path] = None) -> Chroma:
        """
        Create a vector store. If persist=False, it's temporary in memory.
        Stores returned object in self.vector_store for subsequent retrievals.
        """
        store_path = path or self.vs_path
        if persist:
            if not store_path.exists():
                store_path.mkdir(parents=True, exist_ok=True)
            store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=str(store_path)
            )
            store.persist()
        else:
            store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=None
            )

        # keep reference for later retrievals
        self.vector_store = store
        return store

    def load_vector_store(self, path: Optional[Path] = None):
        """Load an existing persisted vector store (KB)."""
        store_path = path or self.vs_path
        if not store_path.exists():
            raise FileNotFoundError(f"Vector store not found at {store_path}")
        self.vector_store = Chroma(
            persist_directory=str(store_path),
            embedding_function=self.embeddings
        )
        return self.vector_store

    def create_retriever(self, vector_store: Optional[Chroma] = None, search_type: str = "mmr", **kwargs):
        """Return a retriever for the given vector store."""
        store = vector_store or self.vector_store
        if store is None:
            raise ValueError("Vector store not loaded or built")
        return store.as_retriever(search_type=search_type, **kwargs)

    def retrieve(self, query: str, k: int = 30) -> List[Document]:
        """
        Retrieve up to k relevant documents, using MMR with high fetch_k to maximize results.
        - Returns exactly k if possible.
        - If fewer chunks exist, returns all available chunks.
        """
        if self.vector_store is None:
            raise RuntimeError("Vector store not loaded or built.")

        # MMR to fetch more than needed to ensure top-k
        retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={'k': k, 'fetch_k': max(k * 5, 50)}
        )

        results = retriever.get_relevant_documents(query) or []

        # Return top k (or fewer if DB has less)
        return results[:k]
