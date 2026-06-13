# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import json
import logging
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class CriteriaManager:
    """Loads evaluation criteria from the configured scans JSON file."""

    def __init__(self, config_path: str):
        """Load scans configuration from the path specified in config.yaml."""

        config_path = Path(config_path).resolve()
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        scans_rel = None
        if isinstance(config, dict):
            scans_rel = config.get("evaluation", {}).get("scans_path")

        if not scans_rel:
            logger.error("'evaluation.scans_path' missing from config.yaml")
            raise KeyError(
                "scans_path must be defined in config.yaml under evaluation.scans_path"
            )

        scans_path = Path(scans_rel)
        if not scans_path.is_absolute():
            project_root = Path(__file__).resolve().parents[2]
            scans_path = (project_root / scans_path).resolve()

        if not scans_path.exists():
            logger.error(f"scans.json not found at {scans_path} (resolved from '{scans_rel}')")
            raise FileNotFoundError(
                f"scans.json not found at {scans_path} (resolved from '{scans_rel}')"
            )

        with open(scans_path, "r", encoding="utf-8") as f:
            self.scans = json.load(f)
        logger.info(f"CriteriaManager loaded {len(self.scans)} scan(s) from {scans_path}")

    def get_criterion_text(self, scan_name: str, criterion_name: str) -> str:
        """Return a formatted string with the criterion's full details including metrics."""

        for scan in self.scans:
            if scan.get("scan", "").strip().lower() == scan_name.strip().lower():
                for c in scan.get("criteria", []):
                    if c.get("name", "").strip().lower() == criterion_name.strip().lower():
                        lines = [
                            f"Criterion: {c.get('name', '')}",
                            f"Description: {c.get('description', '')}",
                            f"Review Question: {c.get('review_question', '')}",
                            "Metrics:",
                        ]
                        for k, v in c.get("metrics", {}).items():
                            lines.append(f"  {k}: {v}")
                        return "\n".join(lines)
                return f"Criterion '{criterion_name}' not found in scan '{scan_name}'."
        return f"Scan '{scan_name}' not found."

    def get_criterion_description(self, scan_name: str, criterion_name: str) -> str:
        """Return only the description field for a given criterion."""

        for scan in self.scans:
            if scan.get("scan", "").strip().lower() == scan_name.strip().lower():
                for c in scan.get("criteria", []):
                    if c.get("name", "").strip().lower() == criterion_name.strip().lower():
                        return c.get("description", "")
                raise ValueError(f"Criterion '{criterion_name}' not found in scan '{scan_name}'.")
        raise ValueError(f"Scan '{scan_name}' not found.")
