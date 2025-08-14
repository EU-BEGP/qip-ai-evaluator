from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

class DocumentSplitter:
    """Token-based splitter, reads config/config.yaml and validates parameters"""

    def __init__(self):
        config_path = Path(__file__).parents[1] / "config" / "config.yaml"
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)

        ts_cfg = cfg["document_processing"]["text_splitter"]

        # Required keys
        required_keys = ["chunk_size", "chunk_overlap", "separators", "token_encoding", "max_chunks"]
        for key in required_keys:
            if key not in ts_cfg:
                raise ValueError(f"Missing '{key}' in text_splitter config")

        # Assign config
        self.chunk_size = ts_cfg["chunk_size"]
        self.chunk_overlap = ts_cfg["chunk_overlap"]
        self.separators = ts_cfg["separators"]
        self.max_chunks = ts_cfg["max_chunks"]

        # Validate parameters
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        if self.max_chunks is not None and self.max_chunks <= 0:
            raise ValueError("max_chunks must be > 0 or None")

        # Token-based length function
        encoding = tiktoken.get_encoding(ts_cfg["token_encoding"])
        self.length_function = lambda text: len(encoding.encode(text))

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=self.length_function,
            separators=self.separators
        )

    def split_content(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        return list(self.split_content_iter(content, metadata))

    def split_content_iter(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        raw_chunks = [c for c in self.splitter.split_text(content) if c.strip()]
        total_chunks = len(raw_chunks)

        for i, chunk in enumerate(raw_chunks):
            if self.max_chunks and i >= self.max_chunks:
                break
            chunk_meta = {**(metadata or {}), "chunk_index": i + 1, "total_chunks": total_chunks}
            yield Document(page_content=chunk, metadata=chunk_meta)
