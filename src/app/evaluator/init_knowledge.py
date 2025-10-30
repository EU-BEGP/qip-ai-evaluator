from pathlib import Path
import json
import logging
import yaml
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# -------------------- PROJECT ROOT --------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from retrievers.vector_store_manager import VectorStoreManager
from evaluation.criteria_extractor import CriteriaExtractor


# -------------------- CONFIG UTILITIES --------------------
def load_config():
    """Load YAML configuration"""
    cfg_path = SRC_DIR / "config" / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found at {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_project_path(path_str):
    """Resolve path relative to src/ if not absolute"""
    path = Path(path_str)
    return path if path.is_absolute() else (SRC_DIR / path).resolve()


# -------------------- STEP 1: BUILD KB --------------------
def build_knowledge_base_auto():
    logging.info("=== Step 1: Auto Build Knowledge Base ===")

    cfg = load_config()
    kb_dir_cfg = cfg.get("knowledge", {}).get("kb_dir")
    if not kb_dir_cfg:
        raise ValueError("Missing 'knowledge.kb_dir' in config.yaml")

    kb_dir = resolve_project_path(kb_dir_cfg)
    kb_dir.mkdir(parents=True, exist_ok=True)

    manager = VectorStoreManager()
    docs = manager.load_documents([
        str(p) for p in kb_dir.glob("*") if p.is_file() and p.suffix.lower() in [".pdf", ".docx", ".txt"]
    ])

    docs = [doc for doc in docs if doc.page_content.strip()]
    if not docs:
        raise ValueError(f"No valid document chunks found in KB directory: {kb_dir}")

    logging.info(f"Loaded {len(docs)} document chunks from KB directory {kb_dir}")

    manager.build_vector_store(docs)
    manager.load_vector_store()
    logging.info("Knowledge base vector store ready.")
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
    scans_path.parent.mkdir(parents=True, exist_ok=True)

    # --- CASE 1: JSON provided ---
    if criteria_file.suffix.lower() == ".json":
        if not criteria_file.exists():
            raise FileNotFoundError(f"Criteria JSON file not found: {criteria_file}")
        with open(criteria_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Save copy to scans_path
        with open(scans_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logging.info(f"Criteria JSON loaded from {criteria_file} and saved to {scans_path}")
        return data

    # --- CASE 2: PDF, DOCX or XLSX provided ---
    elif criteria_file.suffix.lower() in (".pdf", ".docx", ".xlsx"):
        extractor = CriteriaExtractor(str(criteria_file), str(scans_path))
        extractor.process_file()

        if not scans_path.exists():
            raise RuntimeError(f"Failed to generate criteria JSON at {scans_path}")

        logging.info(f"Criteria extracted from {criteria_file} and saved to {scans_path}")
        with open(scans_path, "r", encoding="utf-8") as f:
            return json.load(f)

    else:
        raise ValueError(f"Unsupported criteria file format: {criteria_file.suffix}")
