# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import List

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.platypus import LongTable

from .styles import get_eu_class_style, set_table_style


def split_paragraph_by_height(text: str, style: ParagraphStyle, col_width: float, max_height: float) -> list[str]:
    """Split text into chunks so each chunk renders within max_height at col_width."""

    if not text:
        return [""]

    chunks = []
    current = ""
    words = text.replace("<br/>", " <br/> ").split()

    for word in words:
        candidate = current + (" " if current else "") + word
        _, h = Paragraph(candidate, style).wrap(col_width, max_height)
        if h <= max_height:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = word

    if current:
        chunks.append(current)

    return chunks


def criterion_to_rows(criterion: dict, styles: dict, col_widths: list[float], max_cell_height: float) -> list[list]:
    """Convert a criterion dict into table rows that fit within cell height limits."""

    score = criterion.get("score", 0)
    max_score = criterion.get("max_score", 5)
    eu_class = criterion.get("eu_classification", "")
    base_style = styles["TableCell"]

    name_chunks = split_paragraph_by_height(criterion.get("name", ""), base_style, col_widths[0], max_cell_height)
    desc_chunks = split_paragraph_by_height(criterion.get("description", ""), base_style, col_widths[1], max_cell_height)

    shortcomings_text = "<br/>".join(f"• {s}" for s in criterion.get("shortcomings", []))
    short_chunks = split_paragraph_by_height(shortcomings_text, base_style, col_widths[4], max_cell_height)

    recommendations_text = "<br/>".join(f"• {r}" for r in criterion.get("recommendations", []))
    rec_chunks = split_paragraph_by_height(recommendations_text, base_style, col_widths[5], max_cell_height)

    max_rows = max(len(name_chunks), len(desc_chunks), len(short_chunks), len(rec_chunks))
    eu_style = get_eu_class_style(eu_class, styles)

    rows = []
    for i in range(max_rows):
        rows.append([
            Paragraph(name_chunks[i], base_style) if i < len(name_chunks) else "",
            Paragraph(desc_chunks[i], base_style) if i < len(desc_chunks) else "",
            f"{score:.1f}/{max_score:.1f}" if i == 0 else "",
            Paragraph(eu_class, eu_style) if i == 0 else "",
            Paragraph(short_chunks[i], base_style) if i < len(short_chunks) else "",
            Paragraph(rec_chunks[i], base_style) if i < len(rec_chunks) else "",
        ])

    return rows


def create_criteria_table(criteria_data: List[List], col_widths: List[float]) -> LongTable:
    """Build a LongTable for criteria data with standard styling applied."""

    table = LongTable(criteria_data, colWidths=col_widths, repeatRows=1)
    set_table_style(table)
    return table
