# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import Optional


def normalize_title(title) -> str:
    """Coerce a Learnify page title (str or localized dict) to a clean string."""

    if isinstance(title, dict):
        title = title.get("en", "")
    return title.strip() if isinstance(title, str) else ""


def is_module_section(title) -> bool:
    """True when a section title starts with 'module' or 'chapter' (any variant)."""

    normalized = normalize_title(title).lower()
    return normalized.startswith("module") or normalized.startswith("chapter")


def select_module_section(pages: list) -> Optional[dict]:
    """
    A section is a non-empty pageType-8 node (one that has child pages). The
    named Module/Chapter section wins; otherwise the first non-empty section is
    used as the metadata anchor.
    """

    sections = [
        p for p in pages
        if p.get("pageType") == 8 and len(p.get("pages") or []) > 0
    ]
    for section in sections:
        if is_module_section(section.get("title")):
            return section
    return sections[0] if sections else None
