import json
from pathlib import Path
import yaml

class CriteriaManager:
    def __init__(self, config_path: str):
        config_path = Path(config_path).resolve()
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        scans_path = config.get("scans_path")
        if not scans_path:
            raise KeyError("scans_path must be defined in config.yaml")
        scans_path = Path(scans_path).resolve()
        if not scans_path.exists():
            raise FileNotFoundError(f"scans.json not found at {scans_path}")
        with open(scans_path, "r", encoding="utf-8") as f:
            self.scans = json.load(f)

    def get_criterion_text(self, scan_name: str, criterion_name: str) -> str:
        """
        Search for a scan and criterion in scans.json and return formatted info as text.
        """
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
