# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

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

    def rank_chunks(self, query: str, documents: Optional[List[Document]] = None, top_k: int = 10, batch_size: int = 64) -> List[Tuple[Document, str, float]]:
        """Rank document chunks using Cross-Encoder and return top_k ordered by chunk_index."""
        docs_to_rank = documents or self.documents
        if not docs_to_rank:
            raise ValueError("No document chunks provided or loaded.")

        # Compute relevance scores
        cross_input = [(query, doc.page_content) for doc in docs_to_rank]
        scores = []
        for i in range(0, len(cross_input), batch_size):
            batch = cross_input[i:i + batch_size]
            scores.extend(self.cross_encoder.predict(batch))

        # Attach scores
        scored_docs = [(doc, doc.page_content, score) for doc, score in zip(docs_to_rank, scores)]

        # Sort by score descending
        ranked_by_score = sorted(scored_docs, key=lambda x: x[2], reverse=True)

        # Keep only top_k unique chunk_index
        seen_indices = set()
        top_docs = []
        for doc, text, score in ranked_by_score:
            idx = doc.metadata.get("chunk_index")
            if idx not in seen_indices:
                top_docs.append((doc, text, score))
                seen_indices.add(idx)
            if len(top_docs) >= top_k:
                break

        # Sort top_docs by chunk_index to maintain document order
        return sorted(top_docs, key=lambda x: x[0].metadata["chunk_index"])
