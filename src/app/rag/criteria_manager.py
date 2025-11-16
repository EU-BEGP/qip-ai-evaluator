import json
from pathlib import Path
import yaml

class CriteriaManager:
    def __init__(self, config_path: str):
        # Resolve config and make scans_path relative to project root (src/)
        config_path = Path(config_path).resolve()
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # support both evaluation.scans_path and top-level scans_path
        scans_rel = None
        if isinstance(config, dict):
            scans_rel = config.get("evaluation", {}).get("scans_path")

        if not scans_rel:
            raise KeyError("scans_path must be defined in config.yaml (either evaluation.scans_path or scans_path)")

        scans_path = Path(scans_rel)
        # if relative, resolve against project root (src/)
        if not scans_path.is_absolute():
            project_root = Path(__file__).resolve().parents[1]
            scans_path = (project_root / scans_path).resolve()

        if not scans_path.exists():
            raise FileNotFoundError(f"scans.json not found at {scans_path} (resolved from '{scans_rel}')")

        with open(scans_path, "r", encoding="utf-8") as f:
            self.scans = json.load(f)

    def get_criterion_text(self, scan_name: str, criterion_name: str) -> str:
        """Devuelve texto formateado completo con métricos y pregunta de revisión"""
        for scan in self.scans:
            if scan.get("scan", "").strip().lower() == scan_name.strip().lower():
                for c in scan.get("criteria", []):
                    if c.get("name", "").strip().lower() == criterion_name.strip().lower():
                        lines = [
                            f"Criterion: {c.get('name','')}",
                            f"Description: {c.get('description','')}",
                            f"Review Question: {c.get('review_question','')}",
                            "Metrics:"
                        ]
                        for k, v in c.get("metrics", {}).items():
                            lines.append(f"  {k}: {v}")
                        return "\n".join(lines)
                return f"Criterion '{criterion_name}' not found in scan '{scan_name}'."
        return f"Scan '{scan_name}' not found."

    def get_criterion_description(self, scan_name: str, criterion_name: str) -> str:
        """Devuelve únicamente la descripción del criterio"""
        for scan in self.scans:
            if scan.get("scan", "").strip().lower() == scan_name.strip().lower():
                for c in scan.get("criteria", []):
                    if c.get("name", "").strip().lower() == criterion_name.strip().lower():
                        return c.get("description", "")
                raise ValueError(f"Criterion '{criterion_name}' not found in scan '{scan_name}'.")
        raise ValueError(f"Scan '{scan_name}' not found.")
