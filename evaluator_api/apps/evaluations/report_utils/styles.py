# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Table, TableStyle


def get_custom_styles() -> dict:
    """Return a stylesheet with all custom styles for the evaluation report."""

    styles = getSampleStyleSheet()

    custom_styles = {
        "ReportTitle": ParagraphStyle(
            name="ReportTitle",
            parent=styles["Heading1"],
            fontSize=24,
            leading=30,
            spaceAfter=30,
            alignment=1,
            textColor=colors.HexColor("#1B365D"),
        ),
        "ReportSection": ParagraphStyle(
            name="ReportSection",
            parent=styles["Heading1"],
            fontSize=16,
            spaceAfter=20,
            spaceBefore=20,
            textColor=colors.HexColor("#2E5984"),
            borderColor=colors.HexColor("#2E5984"),
            borderWidth=1,
            borderPadding=10,
        ),
        "ReportSubSection": ParagraphStyle(
            name="ReportSubSection",
            parent=styles["Heading2"],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.HexColor("#444444"),
            borderColor=colors.HexColor("#CCCCCC"),
            borderWidth=0.5,
            borderPadding=5,
        ),
        "ReportBody": ParagraphStyle(
            name="ReportBody",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            spaceAfter=8,
            textColor=colors.HexColor("#333333"),
        ),
        "TableHeader": ParagraphStyle(
            name="TableHeader",
            parent=styles["Normal"],
            fontSize=10,
            leading=12,
            textColor=colors.white,
            alignment=1,
        ),
        "TableCell": ParagraphStyle(
            name="TableCell",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            wordWrap="CJK",
        ),
    }

    for style_name, style in custom_styles.items():
        styles.add(style)

    styles.add(ParagraphStyle(name="SubSection", parent=styles["ReportSubSection"]))
    styles.add(ParagraphStyle(name="Section", parent=styles["ReportSection"]))

    return styles


def get_eu_class_style(eu_class: str, styles: dict) -> ParagraphStyle:
    """Return a coloured ParagraphStyle for an EEDA classification label."""

    colors_map = {
        "No Issues":          ("#E8F5E9", "#2E7D32"),
        "Minor Shortcoming":  ("#FFF3E0", "#E65100"),
        "Shortcoming":        ("#FFE0B2", "#D84315"),
        "Minor Weakness":     ("#FFEBEE", "#C62828"),
        "Weakness":           ("#FFCDD2", "#B71C1C"),
    }
    bg_color, text_color = colors_map.get(eu_class, ("#FFFFFF", "#000000"))

    return ParagraphStyle(
        f"EU_{eu_class}",
        parent=styles["TableCell"],
        textColor=colors.HexColor(text_color),
        backColor=colors.HexColor(bg_color),
        alignment=1,
    )


def set_table_style(table: Table) -> None:
    """Apply consistent styling to a criteria table."""

    table.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#2E5984")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        # Body
        ("BACKGROUND",    (0, 1), (-1, -1), colors.white),
        ("GRID",          (0, 0), (-1, -1), 1, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F8F8")]),
        ("PADDING",       (0, 0), (-1, -1), 6),
        # Text
        ("WORDWRAP",      (0, 0), (-1, -1), 1),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEADING",       (0, 0), (-1, -1), 12),
    ]))

    table._splitLongWords = 1
    table.repeatRows = 1
    table.keepWithNext = False
