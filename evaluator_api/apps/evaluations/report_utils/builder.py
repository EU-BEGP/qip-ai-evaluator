# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import json
from io import BytesIO
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import legal
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle

from .document import HyperlinkedTOC, MyDocTemplate, add_page_number
from .scoring import EvaluationUtils
from .styles import get_custom_styles
from .tables import create_criteria_table, criterion_to_rows


class ReportManager:
    """Orchestrates PDF report generation from evaluation and module metadata."""

    def __init__(self, evaluation_data_path: str, module_data_path: str):
        with open(evaluation_data_path, "r", encoding="utf-8") as f:
            self.evaluation_data = json.load(f)
        EvaluationUtils().fill_aditional_data(self.evaluation_data)

        with open(module_data_path, "r", encoding="utf-8") as f:
            self.module_data = json.load(f)

    def build_first_page(self, styles: dict) -> List:
        """Build the title page and table of contents."""

        story = []
        story.append(Paragraph("Module Evaluation Report:", styles["ReportTitle"]))
        story.append(Paragraph(f"{self.evaluation_data['title']}", styles["ReportTitle"]))
        story.append(Spacer(1, 30))

        story.append(Paragraph("Table of Contents", styles["ReportSection"]))
        toc = HyperlinkedTOC()
        toc.levelStyles = [
            ParagraphStyle("TOCLevel1", fontSize=11, leftIndent=20, firstLineIndent=-20, spaceBefore=6, leading=14),
            ParagraphStyle("TOCLevel2", fontSize=10, leftIndent=40, firstLineIndent=-20, spaceBefore=2, leading=12),
        ]
        story.append(Spacer(1, 6))
        story.append(toc)
        story.append(PageBreak())

        return story

    def build_executive_summary(self, styles: dict) -> List:
        """Build the executive summary section with module overview and scan scores."""

        story = []
        total = self.evaluation_data["total_score"]
        total_max = self.evaluation_data["total_max_score"]
        percentage = (total / total_max * 100) if total_max > 0 else 0

        story.append(Paragraph("1. Executive Summary", styles["Section"]))
        story.append(Paragraph("Module Overview", styles["SubSection"]))

        for label, key in [
            ("Title", "title"),
            ("Abstract", "abstract"),
            ("Uniqueness", "uniqueness"),
            ("Societal Relevance", "societal_relevance"),
            ("ELH", "elh"),
            ("EQF", "eqf"),
            ("SMCTS", "smcts"),
            ("Teachers", "teachers"),
            ("Keywords", "keywords"),
        ]:
            story.append(Paragraph(f"<b>{label}:</b> {self.module_data[key]}", styles["ReportBody"]))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Performance Overview", styles["SubSection"]))
        story.append(Paragraph(
            f"This comprehensive evaluation report analyzes the unit outline across multiple dimensions. "
            f"The document achieved an overall score of {percentage:.1f}%.",
            styles["ReportBody"],
        ))

        if self.evaluation_data["content"]:
            data = [["Scan", "Criteria count", "Score", "Maximum Score", "Average Score", "Percentage"]]
            for scan in self.evaluation_data["content"]:
                scan_pct = scan["score_scan"] / scan["max_score_scan"] * 100
                data.append([
                    scan["scan"],
                    scan["criterion_quantity_scan"],
                    str(scan["score_scan"]),
                    str(scan["max_score_scan"]),
                    f"{scan['average_score_scan']}/5",
                    f"{scan_pct:.1f}%",
                ])

            max_table_width = 540
            col_widths = [max_table_width * w for w in (0.25, 0.15, 0.15, 0.15, 0.15, 0.15)]
            summary_table = Table(data, colWidths=col_widths)
            summary_table.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#2E5984")),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("GRID",          (0, 0), (-1, -1), 1, colors.HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F8F8")]),
            ]))
            story.append(summary_table)

        story.append(PageBreak())
        return story

    def build_detailed_analysis(self, styles: dict, max_cell_height: float, col_widths: List[float], total_table_width: float) -> List:
        """Build the detailed per-scan analysis section with criteria tables."""

        story = []
        story.append(Paragraph("2. Detailed Analysis", styles["Section"]))

        # EEDA classification legend
        story.append(Paragraph("EEDA Classification System (EEDA Class.)", styles["SubSection"]))
        legend_data = [
            ["Classification", "Score Range", "Description"],
            ["No Issues",         "5.0",       "Meets all requirements perfectly"],
            ["Minor Shortcoming", "4.5 - 4.9", "Small improvements needed"],
            ["Shortcoming",       "4.0 - 4.4", "Notable improvements needed"],
            ["Minor Weakness",    "3.0 - 3.9", "Significant improvements needed"],
            ["Weakness",          "< 3.0",     "Major improvements required"],
        ]
        legend_row_colors = [
            (colors.HexColor("#E8F5E9"), colors.HexColor("#2E7D32")),
            (colors.HexColor("#FFF3E0"), colors.HexColor("#E65100")),
            (colors.HexColor("#FFE0B2"), colors.HexColor("#D84315")),
            (colors.HexColor("#FFEBEE"), colors.HexColor("#C62828")),
            (colors.HexColor("#FFCDD2"), colors.HexColor("#B71C1C")),
        ]
        legend_table = Table(legend_data, colWidths=[120, 80, 300])
        legend_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E5984")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("ALIGN",      (0, 0), (-1, 0), "CENTER"),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID",       (0, 0), (-1, -1), 1, colors.HexColor("#CCCCCC")),
            ("PADDING",    (0, 0), (-1, -1), 6),
        ]))
        for i, (bg, fg) in enumerate(legend_row_colors, 1):
            legend_table.setStyle(TableStyle([
                ("BACKGROUND", (0, i), (0, i), bg),
                ("TEXTCOLOR",  (0, i), (0, i), fg),
            ]))
        story.append(legend_table)
        story.append(Spacer(1, 20))

        # Per-scan analysis
        for scan in self.evaluation_data["content"]:
            story.append(Paragraph(f"Analysis: {scan['scan']}", styles["SubSection"]))
            story.append(Paragraph(
                f"Description: {scan.get('description') or 'No available...'}",
                styles["ReportBody"],
            ))
            story.append(Paragraph(
                f"Criteria count: {scan['criterion_quantity_scan']}<br/>"
                f"Score: {scan['score_scan']}/{scan['max_score_scan']} "
                f"({(scan['score_scan'] / scan['max_score_scan'] * 100):.1f}%)<br/>"
                f"Average score: {scan['average_score_scan']}/5",
                styles["ReportBody"],
            ))

            if scan.get("criteria"):
                criteria_data = [["Criterion", "Description", "Score", "EEDA Class.", "Shortcomings", "Recommendations"]]
                for criterion in scan["criteria"]:
                    criteria_data.extend(criterion_to_rows(criterion, styles, col_widths, max_cell_height))

                criteria_table = create_criteria_table(criteria_data, col_widths)
                criteria_table.splitByRow = True
                story.append(criteria_table)
                story.append(Spacer(1, 20))

            story.append(PageBreak())

        return story

    def generate_pdf_report(self, output_path: str) -> None:
        """Generate the full PDF report and write it to output_path."""

        page_height = legal[1]
        max_cell_height = (page_height - 110) * 0.80

        total_table_width = 560
        col_widths = [total_table_width * w for w in (0.10, 0.17, 0.07, 0.16, 0.25, 0.25)]

        buffer = BytesIO()
        doc = MyDocTemplate(
            buffer,
            pagesize=legal,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50,
            allowSplitting=1,
        )
        styles = get_custom_styles()

        story = []
        story.extend(self.build_first_page(styles))
        story.extend(self.build_executive_summary(styles))
        story.extend(self.build_detailed_analysis(styles, max_cell_height, col_widths, total_table_width))

        doc.multiBuild(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
        buffer.seek(0)

        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
