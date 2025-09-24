from pathlib import Path
from typing import List, Tuple, Optional
from langchain.schema import Document
from sentence_transformers import CrossEncoder
import pickle

from document_processing.text_splitter import DocumentSplitter
from document_processing.document_loader import DocumentLoaderFactory


class CrossEncoderRAG:
    """Cross-Encoder retrieval for pre-split document chunks."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2",
        chunks_path: Optional[Path] = None,
        use_memory_only: bool = True
    ):
        self.cross_encoder = CrossEncoder(model_name)
        self.splitter = DocumentSplitter()
        self.documents: List[Document] = []
        self.chunks_path = chunks_path
        self.use_memory_only = use_memory_only

        if not use_memory_only and chunks_path and chunks_path.exists():
            self.load_chunks(chunks_path)

    def load_and_split_files(self, file_paths: List[str]):
        """Load documents and split into chunks."""
        all_chunks = []
        start_index = 0
        for path in file_paths:
            loader = DocumentLoaderFactory.create_loader(path)
            docs = loader.load_document(path)
            for doc in docs:
                chunks = self.splitter.split_content(doc.page_content, doc.metadata, start_index=start_index)
                all_chunks.extend(chunks)
                start_index += len(chunks)
        self.documents = all_chunks

    def save_chunks(self, path: Optional[Path] = None):
        """Optionally save chunks to disk."""
        if self.use_memory_only:
            return
        save_path = path or self.chunks_path
        if save_path is None:
            raise ValueError("No path specified to save chunks.")
        with open(save_path, "wb") as f:
            pickle.dump(self.documents, f)
        self.chunks_path = save_path

    def load_chunks(self, path: Path):
        """Optionally load chunks from disk."""
        if self.use_memory_only:
            return
        with open(path, "rb") as f:
            self.documents = pickle.load(f)
        self.chunks_path = path

    def set_documents(self, documents: List[Document]):
        """Set pre-split documents manually (memory-only)."""
        self.documents = documents

    def rank_chunks(self, query: str, top_k: int = 10, batch_size: int = 64) -> List[Tuple[Document, str, float]]:
        """Rank document chunks using Cross-Encoder."""
        if not self.documents:
            raise ValueError("No document chunks loaded. Use load_and_split_files or set_documents.")

        cross_input = [(query, doc.page_content) for doc in self.documents]
        scores = []

        for i in range(0, len(cross_input), batch_size):
            batch = cross_input[i:i + batch_size]
            scores.extend(self.cross_encoder.predict(batch))

        ranked = sorted(
            [(doc, doc.page_content, score) for doc, score in zip(self.documents, scores)],
            key=lambda x: x[2],
            reverse=True
        )

        seen = set()
        final_docs = []
        for doc, text, score in ranked:
            idx = doc.metadata.get("chunk_index")
            if idx not in seen:
                final_docs.append((doc, text, score))
                seen.add(idx)
            if len(final_docs) >= top_k:
                break

        return final_docs


# EXAMPLE
if __name__ == "__main__":
    rag = CrossEncoderRAG(use_memory_only=True)

    file_paths = ["rag/Test.pdf"]
    print(f"Loading and splitting {len(file_paths)} document(s) into memory...")
    rag.load_and_split_files(file_paths)
    print(f"Loaded {len(rag.documents)} chunks into memory.")

    print("\nEnter 'exit' to quit.")
    while True:
        query = input("\nEnter search query: ").strip()
        if query.lower() == "exit":
            break

        top_k = 10
        results = rag.rank_chunks(query, top_k=top_k)

        print(f"\n=== Top {top_k} results ===")
        for i, (doc, text, score) in enumerate(results, 1):
            idx = doc.metadata.get("chunk_index")
            print(f"\n--- Rank {i} | Score: {score:.4f} | chunk_index: {idx} ---")
            print(text[:500] + ("..." if len(text) > 500 else ""))
            print("-" * 80)
