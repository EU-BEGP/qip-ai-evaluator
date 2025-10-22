from pathlib import Path
import yaml
from typing import List, Dict, Optional
from langchain.schema import Document
from langchain_community.vectorstores import Chroma

from document_processing.document_loader import DocumentLoaderFactory
from document_processing.text_splitter import DocumentSplitter
from document_processing.embeddings_manager import EmbeddingsManager


class VectorStoreManager:
    """Manage vector stores: KB and temporary ones for evaluation."""

    def __init__(self, kb_path: Optional[Path] = None):
        # Load config anchored to project root (src/)
        project_root = Path(__file__).resolve().parents[1]
        config_path = project_root / "config" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f) or {}

        # KB path: prefer explicit kb_path, otherwise resolve configured path
        if kb_path:
            self.vs_path = Path(kb_path).resolve()
        else:
            configured = Path(self.cfg.get("vector_store", {}).get("path", "data/vector_store"))
            # if configured path is relative, resolve it against project_root
            if not configured.is_absolute():
                self.vs_path = (project_root / configured).resolve()
            else:
                self.vs_path = configured.resolve()

        # Embeddings & splitter
        self.embeddings = EmbeddingsManager().get_langchain_embeddings()
        self.splitter = DocumentSplitter()

        # Stores
        self.vector_store: Optional[Chroma] = None

    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """Load and split documents."""
        all_chunks = []
        for path in file_paths:
            loader = DocumentLoaderFactory.create_loader(path)
            docs = loader.load_document(path)
            for doc in docs:
                chunks = self.splitter.split_content(doc.page_content, doc.metadata)
                all_chunks.extend(chunks)
        return all_chunks

    def build_vector_store(self, documents: List[Document], persist: bool = True, path: Optional[Path] = None) -> Chroma:
        """Create a vector store. If persist=False, it's temporary in memory."""
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

    def create_retriever(self, vector_store: Optional[Chroma] = None, search_type: str = "mmr", **kwargs):
        """Return a retriever for the given vector store."""
        store = vector_store or self.vector_store
        if store is None:
            raise ValueError("Vector store not loaded or built")
        return store.as_retriever(search_type=search_type, **kwargs)

    def multi_query_retrieval(self, queries: List[str], vector_store: Optional[Chroma] = None, k: int = 5, search_type: str = "mmr") -> List[List[Document]]:
        retriever = self.create_retriever(vector_store=vector_store, search_type=search_type, k=k)
        results = [retriever.get_relevant_documents(q) for q in queries]
        return results

# ===== Interactive mode =====
if __name__ == "__main__":
    manager = VectorStoreManager()
    choice = input("Build a new vector store or load existing? [b/l]: ").strip().lower()

    if choice == "b":
        files_input = input("Enter document file paths (comma separated): ")
        file_paths = [p.strip() for p in files_input.split(",") if p.strip()]
        docs = manager.load_documents(file_paths)
        print(f"Loaded {len(docs)} chunks.")
        manager.build_vector_store(docs)
        print("Vector store built.")
    else:
        manager.load_vector_store()
        print("Vector store loaded.")

    print("\nInteractive query (type 'exit' to quit)")
    while True:
        query = input("Enter your query: ").strip()
        if query.lower() == "exit":
            break

        multi_query_input = input("Optional: multiple sub-queries (comma separated) or Enter to use same: ").strip()
        queries = [q.strip() for q in multi_query_input.split(",") if q.strip()] if multi_query_input else [query]

        results = manager.multi_query_retrieval(queries, k=5)
        for i, docs_for_query in enumerate(results):
            print(f"\n--- Results for query {i+1}: '{queries[i]}' ---")
            for j, doc in enumerate(docs_for_query):
                print(f"[{j+1}] {doc.page_content[:100]}...")
