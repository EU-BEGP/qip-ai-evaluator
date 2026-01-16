# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from pathlib import Path
import json
import logging
import yaml
import sys
from django.conf import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

PROJECT_ROOT = settings.BASE_DIR
SRC_DIR = PROJECT_ROOT 

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from retrievers.vector_store_manager import VectorStoreManager
from evaluation.criteria_extractor import CriteriaExtractor

_VECTOR_MANAGER_INSTANCE = None
_CRITERIA_DATA_INSTANCE = None


def load_config():
    cfg_path = SRC_DIR / "config" / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found at {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_project_path(path_str):
    path = Path(path_str)
    if path.is_absolute():
        return path
    return (SRC_DIR / path).resolve()


def build_knowledge_base_auto():
    global _VECTOR_MANAGER_INSTANCE
    
    if _VECTOR_MANAGER_INSTANCE is not None:
        logging.info("Using cached VectorStoreManager (Skipping reload).")
        return _VECTOR_MANAGER_INSTANCE

    logging.info("=== Step 1: Knowledge Base Initialization ===")

    cfg = load_config()
    manager = VectorStoreManager()
    
    expected_db_file = manager.vs_path / "chroma.sqlite3"
    
    if manager.vs_path.exists() and expected_db_file.exists():
        logging.info(f"✅ Existing Vector Store found at {manager.vs_path}. Loading...")
        manager.load_vector_store()
        _VECTOR_MANAGER_INSTANCE = manager
        return manager

    logging.info(f"⚠️ No existing Vector Store found. Building from scratch...")

    kb_dir_cfg = cfg.get("knowledge", {}).get("kb_dir")
    if not kb_dir_cfg:
        raise ValueError("Missing 'knowledge.kb_dir' in config.yaml")

    kb_dir = resolve_project_path(kb_dir_cfg)
    if not kb_dir.exists():
         logging.warning(f"KB directory {kb_dir} does not exist. Creating it...")
         kb_dir.mkdir(parents=True, exist_ok=True)
    
    files = [
        str(p) for p in kb_dir.glob("*") 
        if p.is_file() and p.suffix.lower() in [".pdf", ".docx", ".txt"]
    ]

    if not files:
        logging.warning(f"No documents found in {kb_dir}. Skipping Vector Store build.")
        _VECTOR_MANAGER_INSTANCE = manager
        return manager

    logging.info(f"Processing {len(files)} documents (OCR/Embeddings)... This may take time.")
    docs = manager.load_documents(files)

    docs = [doc for doc in docs if doc.page_content.strip()]
    if not docs:
        logging.warning(f"Documents found but text extraction failed or empty. {kb_dir}")
        _VECTOR_MANAGER_INSTANCE = manager
        return manager

    logging.info(f"Loaded {len(docs)} document chunks. Persisting to disk...")
    
    manager.build_vector_store(docs)
    logging.info("Knowledge base built and saved successfully.")
    
    _VECTOR_MANAGER_INSTANCE = manager
    return manager


def load_criteria_auto():
    global _CRITERIA_DATA_INSTANCE
    
    if _CRITERIA_DATA_INSTANCE is not None:
        return _CRITERIA_DATA_INSTANCE

    logging.info("=== Step 2: Auto Load/Extract Criteria ===")

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
            logging.info(f"✅ Found existing criteria JSON at {scans_path}. Loading directly.")
            with open(scans_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _CRITERIA_DATA_INSTANCE = data
            return data
        except json.JSONDecodeError:
            logging.warning("Existing JSON corrupted. Re-extracting...")

    if not criteria_file.exists():
        logging.error(f"Criteria source file missing: {criteria_file}")
        raise FileNotFoundError(f"Criteria file not found at {criteria_file}")

    if criteria_file.suffix.lower() == ".json":
        with open(criteria_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        with open(scans_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logging.info(f"Criteria JSON loaded from {criteria_file} and saved to {scans_path}")
        _CRITERIA_DATA_INSTANCE = data
        return data

    elif criteria_file.suffix.lower() in (".docx", ".xlsx"):
        extractor = CriteriaExtractor(str(criteria_file), str(scans_path))
        extractor.process_file()

        if not scans_path.exists():
            raise RuntimeError(f"Failed to generate criteria JSON at {scans_path}")

        logging.info(f"Criteria extracted from {criteria_file} and saved to {scans_path}")
        with open(scans_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _CRITERIA_DATA_INSTANCE = data
            return data

    else:
        raise ValueError(f"Unsupported criteria file format: {criteria_file.suffix}")