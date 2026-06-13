# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import json
import logging

from rag.rubric import create_extractor
from .config import load_config, resolve_project_path

logger = logging.getLogger(__name__)

_CRITERIA_DATA_INSTANCE = None


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
        extractor = create_extractor(str(criteria_file), str(scans_path))
        extractor.process_file()
        if not scans_path.exists():
            raise RuntimeError(f"Failed to generate criteria JSON at {scans_path}")
        logger.info(f"Criteria extracted from {criteria_file} and saved to {scans_path}")
        with open(scans_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _CRITERIA_DATA_INSTANCE = data
        return data

    raise ValueError(f"Unsupported criteria file format: {criteria_file.suffix}")
