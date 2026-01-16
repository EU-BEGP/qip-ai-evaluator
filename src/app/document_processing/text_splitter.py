# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

class DocumentSplitter:
    """Token-based splitter, reads config/config.yaml and validates parameters."""

    def __init__(self):
        config_path = Path(__file__).parents[1] / "config" / "config.yaml"
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)

        ts_cfg = cfg["document_processing"]["text_splitter"]

        required_keys = ["chunk_size", "chunk_overlap", "separators", "token_encoding", "max_chunks"]
        for key in required_keys:
            if key not in ts_cfg:
                raise ValueError(f"Missing '{key}' in text_splitter config")

        self.chunk_size = ts_cfg["chunk_size"]
        self.chunk_overlap = ts_cfg["chunk_overlap"]
        self.separators = ts_cfg["separators"]
        self.max_chunks = ts_cfg["max_chunks"]

        encoding = tiktoken.get_encoding(ts_cfg["token_encoding"])
        self.length_function = lambda text: len(encoding.encode(text))

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=self.length_function,
            separators=self.separators
        )

    def split_content(self, content: str, metadata: Optional[Dict[str, Any]] = None, start_index: int = 0) -> List[Document]:
        """Split content into chunks and assign consecutive chunk_index starting at start_index."""
        raw_chunks = [c for c in self.splitter.split_text(content) if c.strip()]
        total_chunks = len(raw_chunks)
        docs = []
        for i, chunk in enumerate(raw_chunks):
            if self.max_chunks and i >= self.max_chunks:
                break
            chunk_meta = {**(metadata or {}), "chunk_index": start_index + i + 1, "total_chunks": total_chunks}
            docs.append(Document(page_content=chunk, metadata=chunk_meta))
        return docs
