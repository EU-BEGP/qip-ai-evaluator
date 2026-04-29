# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import hashlib
import json
import logging
import sys
from pathlib import Path
import yaml

from django.conf import settings

from rag.retrievers.vector_store_manager import VectorStoreManager
from rag.rubric_manger.criteria_extractor import CriteriaExtractor

logger = logging.getLogger(__name__)

PROJECT_ROOT = settings.BASE_DIR
SRC_DIR = PROJECT_ROOT

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Module-level singletons
_VECTOR_MANAGER_INSTANCE = None
_CRITERIA_DATA_INSTANCE = None

# Supported KB file extensions
_KB_EXTENSIONS = {".pdf", ".docx", ".txt"}

# Fingerprint file name stored alongside the vector store
_FINGERPRINT_FILE = ".kb_fingerprint"


def load_config() -> dict:
    """Load and parse the project config.yaml."""

    cfg_path = SRC_DIR / "config" / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found at {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_project_path(path_str: str) -> Path:
    """Resolve a path string relative to the project root."""

    path = Path(path_str)
    if path.is_absolute():
        return path
    return (SRC_DIR / path).resolve()


def _compute_kb_fingerprint(kb_dir: Path) -> str:
    """
    Compute an MD5 fingerprint of the KB directory contents.
    Incorporates each file's name and modification time so that adding,
    removing, or updating a file produces a different fingerprint.
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


def build_knowledge_base_auto() -> VectorStoreManager:
    """
    Initialize and return the shared VectorStoreManager.
    On startup:
    - If the vector store exists and the KB has not changed, it is loaded.
    - If the KB has new or modified files, the vector store is rebuilt.
    - If no vector store exists, it is built from scratch.
    """

    global _VECTOR_MANAGER_INSTANCE

    if _VECTOR_MANAGER_INSTANCE is not None:
        logger.info("Using cached VectorStoreManager (skipping reload).")
        return _VECTOR_MANAGER_INSTANCE

    logger.info("=== Step 1: Knowledge Base Initialization ===")

    cfg = load_config()
    manager = VectorStoreManager()
    expected_db_file = manager.vs_path / "chroma.sqlite3"

    # Resolve KB directory
    kb_dir_cfg = cfg.get("knowledge", {}).get("kb_dir")
    if not kb_dir_cfg:
        raise ValueError("Missing 'knowledge.kb_dir' in config.yaml")

    kb_dir = resolve_project_path(kb_dir_cfg)
    if not kb_dir.exists():
        logger.warning(f"KB directory {kb_dir} does not exist. Creating it...")
        kb_dir.mkdir(parents=True, exist_ok=True)

    if manager.vs_path.exists() and expected_db_file.exists():
        if _has_kb_changed(kb_dir, manager.vs_path):
            logger.info("KB files changed since last build. Rebuilding vector store...")
        else:
            logger.info(f"KB unchanged. Loading existing vector store from {manager.vs_path}...")
            manager.load_vector_store()
            _VECTOR_MANAGER_INSTANCE = manager
            return manager

    # Build vector store from KB files
    files = [
        str(p) for p in kb_dir.glob("*")
        if p.is_file() and p.suffix.lower() in _KB_EXTENSIONS
    ]

    if not files:
        logger.warning(f"No documents found in {kb_dir}. Skipping vector store build.")
        _VECTOR_MANAGER_INSTANCE = manager
        return manager

    logger.info(f"Processing {len(files)} KB documents (OCR/Embeddings)...")
    docs = manager.load_documents(files)
    docs = [doc for doc in docs if doc.page_content.strip()]

    if not docs:
        logger.warning(f"Documents found but text extraction was empty. Dir: {kb_dir}")
        _VECTOR_MANAGER_INSTANCE = manager
        return manager

    logger.info(f"Loaded {len(docs)} document chunks. Persisting vector store...")
    manager.build_vector_store(docs)
    _save_kb_fingerprint(kb_dir, manager.vs_path)
    logger.info("Knowledge base built and saved successfully.")

    _VECTOR_MANAGER_INSTANCE = manager
    return manager


def load_criteria_auto():
    """
    Load or extract evaluation criteria and cache the result.
    Supports criteria files in JSON, DOCX, or XLSX format.
    On first call, parses and writes the criteria to the configured scans_path.
    """

    global _CRITERIA_DATA_INSTANCE

    if _CRITERIA_DATA_INSTANCE is not None:
        return _CRITERIA_DATA_INSTANCE

    logger.info("=== Step 2: Auto Load/Extract Criteria ===")

    cfg = load_config()
    evaluation_cfg = cfg.get("evaluation", {})
    knowledge_cfg = cfg.get("knowledge", {})
    criteria_file_cfg = knowledge_cfg.get("criteria_file")
    scans_path_cfg = evaluation_cfg.get("scans_path")

    if not criteria_file_cfg or not scans_path_cfg:
        raise ValueError("Missing 'knowledge.criteria_file' or 'evaluation.scans_path' in config.yaml")

    criteria_file = resolve_project_path(criteria_file_cfg)
    scans_path = resolve_project_path(scans_path_cfg)
    scans_path.parent.mkdir(parents=True, exist_ok=True)

    if scans_path.exists():
        try:
            logger.info(f"Found existing criteria JSON at {scans_path}. Loading directly.")
            with open(scans_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _CRITERIA_DATA_INSTANCE = data
            return data
        except json.JSONDecodeError:
            logger.warning("Existing criteria JSON corrupted. Re-extracting...")

    if not criteria_file.exists():
        logger.error(f"Criteria source file missing: {criteria_file}")
        raise FileNotFoundError(f"Criteria file not found at {criteria_file}")

    if criteria_file.suffix.lower() == ".json":
        with open(criteria_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(scans_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Criteria JSON loaded from {criteria_file} and saved to {scans_path}")
        _CRITERIA_DATA_INSTANCE = data
        return data

    if criteria_file.suffix.lower() in (".docx", ".xlsx"):
        extractor = CriteriaExtractor(str(criteria_file), str(scans_path))
        extractor.process_file()
        if not scans_path.exists():
            raise RuntimeError(f"Failed to generate criteria JSON at {scans_path}")
        logger.info(f"Criteria extracted from {criteria_file} and saved to {scans_path}")
        with open(scans_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _CRITERIA_DATA_INSTANCE = data
        return data

    raise ValueError(f"Unsupported criteria file format: {criteria_file.suffix}")
