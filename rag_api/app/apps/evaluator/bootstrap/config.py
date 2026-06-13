# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

"""
Shared startup utilities: project root resolution, sys.path setup, and the
config.yaml loader. Pure helpers reused by both knowledge_base and criteria
bootstrap modules.
"""

import sys
from pathlib import Path

import yaml

from django.conf import settings

PROJECT_ROOT = settings.BASE_DIR
SRC_DIR = PROJECT_ROOT

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


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
