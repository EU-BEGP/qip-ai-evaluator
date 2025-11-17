from pathlib import Path
import json
import logging
import yaml
import sys
from django.conf import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# -------------------- PROJECT ROOT --------------------
# In Docker, BASE_DIR is '/app'. 
# Everything (rag, config, retrievers) is directly inside BASE_DIR.
PROJECT_ROOT = settings.BASE_DIR

# 1. REMOVE 'src' from the path logic.
#    SRC_DIR is now just PROJECT_ROOT because we moved everything up one level in Docker.
SRC_DIR = PROJECT_ROOT 

# 2. Ensure the root is in sys.path so imports like 'retrievers.xxx' work
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from retrievers.vector_store_manager import VectorStoreManager
from evaluation.criteria_extractor import CriteriaExtractor


# -------------------- CONFIG UTILITIES --------------------
def load_config():
    """Load YAML configuration"""
    # Updated path: /app/config/config.yaml
    cfg_path = SRC_DIR / "config" / "config.yaml"
    
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found at {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_project_path(path_str):
    """Resolve path relative to PROJECT_ROOT if not absolute"""
    path = Path(path_str)
    if path.is_absolute():
        return path
    
    # Resolve relative paths (e.g., "data/scans") against /app
    return (SRC_DIR / path).resolve()


# -------------------- STEP 1: BUILD KB --------------------
def build_knowledge_base_auto():
    logging.info("=== Step 1: Knowledge Base Initialization ===")

    cfg = load_config()
    
    # 1. Initialize Manager to get paths
    manager = VectorStoreManager()
    
    # 2. CRITICAL CHECK: Does the Vector Store already exist?
    expected_db_file = manager.vs_path / "chroma.sqlite3"
    
    if manager.vs_path.exists() and expected_db_file.exists():
        logging.info(f"✅ Existing Vector Store found at {manager.vs_path}. Loading...")
        manager.load_vector_store()
        return manager

    logging.info(f"⚠️ No existing Vector Store found. Building from scratch...")

    kb_dir_cfg = cfg.get("knowledge", {}).get("kb_dir")
    if not kb_dir_cfg:
        raise ValueError("Missing 'knowledge.kb_dir' in config.yaml")

    kb_dir = resolve_project_path(kb_dir_cfg)
    if not kb_dir.exists():
         logging.warning(f"KB directory {kb_dir} does not exist. Creating it...")
         kb_dir.mkdir(parents=True, exist_ok=True)
    
    # Only load if files exist
    files = [
        str(p) for p in kb_dir.glob("*") 
        if p.is_file() and p.suffix.lower() in [".pdf", ".docx", ".txt"]
    ]

    if not files:
        logging.warning(f"No documents found in {kb_dir}. Skipping Vector Store build.")
        return manager

    logging.info(f"Processing {len(files)} documents (OCR/Embeddings)... This may take time.")
    docs = manager.load_documents(files)

    docs = [doc for doc in docs if doc.page_content.strip()]
    if not docs:
        logging.warning(f"Documents found but text extraction failed or empty. {kb_dir}")
        return manager

    logging.info(f"Loaded {len(docs)} document chunks. Persisting to disk...")
    
    manager.build_vector_store(docs)
    logging.info("Knowledge base built and saved successfully.")
    return manager

# -------------------- STEP 2: LOAD OR EXTRACT CRITERIA --------------------
def load_criteria_auto():
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
    
    # Ensure parent directory for scans exists
    scans_path.parent.mkdir(parents=True, exist_ok=True)

    if not criteria_file.exists():
        logging.error(f"Criteria source file missing: {criteria_file}")
        # Fallback: check if scans.json already exists
        if scans_path.exists():
             logging.info("Using existing scans.json as fallback.")
             with open(scans_path, "r", encoding="utf-8") as f:
                return json.load(f)
        raise FileNotFoundError(f"Criteria file not found at {criteria_file}")

    # --- CASE 1: JSON provided ---
    if criteria_file.suffix.lower() == ".json":
        with open(criteria_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Save copy to scans_path
        with open(scans_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logging.info(f"Criteria JSON loaded from {criteria_file} and saved to {scans_path}")
        return data

    # --- CASE 2: DOCX or XLSX provided (PDF REMOVED) ---
    elif criteria_file.suffix.lower() in (".docx", ".xlsx"):
        extractor = CriteriaExtractor(str(criteria_file), str(scans_path))
        extractor.process_file()

        if not scans_path.exists():
            raise RuntimeError(f"Failed to generate criteria JSON at {scans_path}")

        logging.info(f"Criteria extracted from {criteria_file} and saved to {scans_path}")
        with open(scans_path, "r", encoding="utf-8") as f:
            return json.load(f)

    else:
        raise ValueError(f"Unsupported criteria file format: {criteria_file.suffix}")
