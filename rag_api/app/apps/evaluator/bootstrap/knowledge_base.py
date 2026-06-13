# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple

from rag.retrieval import BM25Ranker, VectorStore
from .config import load_config, resolve_project_path

logger = logging.getLogger(__name__)

_KB_EXTENSIONS = {".pdf", ".docx", ".txt"}
_FINGERPRINT_FILE = ".kb_fingerprint"
_VECTOR_STORE_INSTANCE: Optional[VectorStore] = None
_KB_BM25_INSTANCE: Optional[BM25Ranker] = None


def _compute_kb_fingerprint(kb_dir: Path) -> str:
    """
    Compute an MD5 fingerprint of the KB directory contents.
    Incorporates each file's name and modification time so that adding, removing, or updating a file produces a different fingerprint.
    """

    files = sorted(
        p for p in kb_dir.glob("*")
        if p.is_file() and p.suffix.lower() in _KB_EXTENSIONS
    )
    descriptor = "|".join(f"{p.name}:{int(p.stat().st_mtime * 1000)}" for p in files)
    return hashlib.md5(descriptor.encode()).hexdigest()


def _read_saved_fingerprint(vs_path: Path) -> str:
    """Return the previously saved KB fingerprint, or empty string if absent."""

    fp_file = vs_path / _FINGERPRINT_FILE
    if fp_file.exists():
        return fp_file.read_text().strip()
    return ""


def _save_kb_fingerprint(kb_dir: Path, vs_path: Path) -> None:
    """Persist the current KB fingerprint next to the vector store."""

    (vs_path / _FINGERPRINT_FILE).write_text(_compute_kb_fingerprint(kb_dir))


def _has_kb_changed(kb_dir: Path, vs_path: Path) -> bool:
    """Return True if KB files have changed since the vector store was last built."""

    return _compute_kb_fingerprint(kb_dir) != _read_saved_fingerprint(vs_path)


def build_knowledge_base_auto() -> Tuple[VectorStore, Optional[BM25Ranker]]:
    """
    Initialize and return the shared (VectorStore, BM25Ranker) pair.
    On startup:
      If the vector store exists and the KB has not changed, it is loaded.
      If the KB has new or modified files, the vector store is rebuilt.
      If no vector store exists, it is built from scratch.
    """

    global _VECTOR_STORE_INSTANCE, _KB_BM25_INSTANCE

    if _VECTOR_STORE_INSTANCE is not None:
        logger.info("Using cached VectorStore (skipping reload).")
        return _VECTOR_STORE_INSTANCE, _KB_BM25_INSTANCE

    logger.info("=== Step 1: Knowledge Base Initialization ===")

    cfg = load_config()
    store = VectorStore()
    expected_db_file = store.vs_path / "chroma.sqlite3"

    # Resolve KB directory
    kb_dir_cfg = cfg.get("knowledge", {}).get("kb_dir")
    if not kb_dir_cfg:
        raise ValueError("Missing 'knowledge.kb_dir' in config.yaml")

    kb_dir = resolve_project_path(kb_dir_cfg)
    if not kb_dir.exists():
        logger.warning(f"KB directory {kb_dir} does not exist. Creating it...")
        kb_dir.mkdir(parents=True, exist_ok=True)

    if store.vs_path.exists() and expected_db_file.exists():
        if _has_kb_changed(kb_dir, store.vs_path):
            logger.info("KB files changed since last build. Rebuilding vector store...")
        else:
            logger.info(f"KB unchanged. Loading existing vector store from {store.vs_path}...")
            store.load()
            kb_docs = store.get_docs()
            kb_bm25 = BM25Ranker(kb_docs) if kb_docs else None
            if kb_bm25:
                logger.info(f"KB BM25 index built with {len(kb_docs)} chunks.")
            _VECTOR_STORE_INSTANCE, _KB_BM25_INSTANCE = store, kb_bm25
            return store, kb_bm25

    # Build vector store from KB files
    files = [
        str(p) for p in kb_dir.glob("*")
        if p.is_file() and p.suffix.lower() in _KB_EXTENSIONS
    ]

    if not files:
        logger.warning(f"No documents found in {kb_dir}. Skipping vector store build.")
        _VECTOR_STORE_INSTANCE, _KB_BM25_INSTANCE = store, None
        return store, None

    logger.info(f"Processing {len(files)} KB documents (OCR/Embeddings)...")
    docs = store.load_documents(files)
    docs = [doc for doc in docs if doc.page_content.strip()]

    if not docs:
        logger.warning(f"Documents found but text extraction was empty. Dir: {kb_dir}")
        _VECTOR_STORE_INSTANCE, _KB_BM25_INSTANCE = store, None
        return store, None

    logger.info(f"Loaded {len(docs)} document chunks. Persisting vector store...")
    store.build(docs)
    kb_bm25 = BM25Ranker(docs)
    logger.info(f"KB BM25 index built with {len(docs)} chunks.")
    _save_kb_fingerprint(kb_dir, store.vs_path)
    logger.info("Knowledge base built and saved successfully.")

    _VECTOR_STORE_INSTANCE, _KB_BM25_INSTANCE = store, kb_bm25
    return store, kb_bm25
