import json
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.pagesizes import letter, landscape
from io import BytesIO
from typing import List

class ReportManager:
    def __init__(self, evaluation_data_path: str):
        with open(evaluation_data_path, 'r', encoding='utf-8') as file:
            self.evaluation_data = json.load(file)
        self.max_score = 0.0
        self.total_score = 0.0

    def get_eu_classification(self, score: float) -> str:
        """Classify based on the score."""
        if score == 5.0:
            return "No Issues"
        elif 4.5 <= score < 5.0:
            return "Minor Shortcoming"
        elif 4.0 <= score < 4.5:
            return "Shortcoming"
        elif 3.0 <= score < 4.0:
            return "Minor Weakness"
        elif score < 3.0:
            return "Weakness"
        else:
            return "Out of valid range"
        
    def fill_aditional_data(self) -> None:
        """Fill the EU classifications, total scores and maximum scores for each evaluation unit."""
        total_max_score = 0.0
        total_score = 0.0
        for scan in self.evaluation_data:
            max_score_scan = 0.0
            score_scan = 0.0
            for criterion in scan.get("criteria", []):  
                score = criterion.get("score")
                if score is not None:
                    criterion["eu_classification"] = self.get_eu_classification(score)
                    criterion["max_score"] = 5.0
                    max_score_scan += 5.0
                    score_scan += score
            
            scan["max_score_scan"] = max_score_scan
            scan["score_scan"] = score_scan
            total_max_score += max_score_scan
            total_score += score_scan

        self.max_score = total_max_score
        self.total_score = total_score
        
        #with open("output.json", "w", encoding="utf-8") as file:
        #    json.dump(self.evaluation_data, file, indent=2, ensure_ascii=False)

    def set_table_style(self, table: Table) -> None:
        """Apply consistent table styling with support for long content."""
        table.setStyle(TableStyle([
            # Header formatting
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5984')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Body formatting
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F8F8')]),
            ('PADDING', (0, 0), (-1, -1), 6),
            
            # Text formatting
            ('WORDWRAP', (0, 0), (-1, -1), 1), 
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEADING', (0, 0), (-1, -1), 12),
        ]))
        
        # Enable table splitting across pages
        table._splitLongWords = 1
        table.repeatRows = 1  # Repeat header row on each page
        table.keepWithNext = False  # Allow splitting

    def get_eu_class_style(self, eu_class: str, styles) -> ParagraphStyle:
        """Get styled paragraph for EU Classification."""
        colors_map = {
            'No Issues': ('#E8F5E9', '#2E7D32'),
            'Minor Shortcoming': ('#FFF3E0', '#E65100'),
            'Shortcoming': ('#FFE0B2', '#D84315'),
            'Minor Weakness': ('#FFEBEE', '#C62828'),
            'Weakness': ('#FFCDD2', '#B71C1C')
        }
        bg_color, text_color = colors_map.get(eu_class, ('#FFFFFF', '#000000'))
        
        return ParagraphStyle(
            f'EU_{eu_class}',
            parent=styles['TableCell'],
            textColor=colors.HexColor(text_color),
            backColor=colors.HexColor(bg_color),
            alignment=1
        )

    def get_custom_styles(self) -> dict:
        """Return a stylesheet with custom styles for the evaluation report."""
        styles = getSampleStyleSheet()

        custom_styles = {
            "ReportTitle": ParagraphStyle(
                name="ReportTitle",
                parent=styles["Heading1"],
                fontSize=24,
                spaceAfter=30,
                alignment=1,
                textColor=colors.HexColor("#1B365D")
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
                borderPadding=10
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
                borderPadding=5
            ),
            "ReportBody": ParagraphStyle(
                name="ReportBody",
                parent=styles["Normal"],
                fontSize=10,
                leading=14,
                spaceAfter=8,
                textColor=colors.HexColor("#333333")
            ),
            "TableHeader": ParagraphStyle(
                name="TableHeader",
                parent=styles["Normal"],
                fontSize=10,
                leading=12,
                textColor=colors.white,
                alignment=1
            ),
            "TableCell": ParagraphStyle(
                name="TableCell",
                parent=styles["Normal"],
                fontSize=9,
                leading=12,
                wordWrap="CJK"
            )
        }

        for style_name, style in custom_styles.items():
            styles.add(style)

        return styles
    
    def create_criteria_table(self, criteria_data: List[List], styles: dict) -> Table:
        """Create a table with proper formatting for criteria data"""
        # Calculate optimal column widths based on content
        total_width = 720  # Total available width
        col_widths = [
            total_width * 0.10,  # Criterion (10%)
            total_width * 0.21,  # Description (21%)
            total_width * 0.06,  # Score (8%)
            total_width * 0.13,  # EU Classification (13%)
            total_width * 0.25,  # Shortcomings (24%)
            total_width * 0.25   # Recommendations (24%)
        ]
        
        table = Table(criteria_data, colWidths=col_widths, repeatRows=1)
        self.set_table_style(table)
        return table

    def build_first_page(self, styles) -> List:
        """Build the first page with report title and table of contents."""
        story = []

        # Title Report
        story.append(Paragraph(f"Module Evaluation Report", styles['ReportTitle']))
        story.append(Spacer(1, 30))

        # Table of Contents
        story.append(Paragraph("Table of Contents", styles['ReportSection']))

        toc_data = [
            ["1. Executive Summary"],
            ["2. Detailed Analysis"],
            ["3. Supporting Evidence"]
        ]

        toc_table = Table(toc_data, colWidths=[400])
        toc_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(toc_table)
        story.append(PageBreak())

        return story
    
    def build_executive_summary(self, styles) -> List:
        """Build the executive summary section."""
        story = []
        percentage = (self.total_score / self.max_score * 100) if self.max_score > 0 else 0

        summary_text = f"""
        This comprehensive evaluation report analyzes the unit outline across multiple dimensions.
        The document achieved an overall score of {percentage:.1f}%.
        """

        story.append(Paragraph("1. Executive Summary", styles['ReportSection']))
        story.append(Paragraph(summary_text, styles['ReportBody']))

        story.append(Paragraph("Performance Overview", styles['ReportSubSection']))

        if self.evaluation_data:
            data = [['Scan', 'Score', 'Maximum', 'Percentage']]
            for scan in self.evaluation_data:
                scan_percentage = (scan['score_scan']/scan['max_score_scan']*100)
                data.append([
                    scan['scan'],
                    str(scan['score_scan']),
                    str(scan['max_score_scan']),
                    f"{scan_percentage:.1f}%"
                ])
            
            chart_table = Table(data, colWidths=[210, 80, 80, 90])
            chart_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5984')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F8F8')]),
            ]))
            story.append(chart_table)

        story.append(PageBreak())
        return story
    
    def build_detailed_analysis(self, styles) -> List:
        """Build the detailed analysis section with criteria tables."""
        story = []
        story.append(Paragraph("2. Detailed Analysis", styles['ReportSection']))

        # EU Classification Table
        story.append(Paragraph("EU Classification System", styles['ReportSubSection']))
        legend_data = [
            ['Classification', 'Score Range', 'Description'],
            ['No Issues', '5.0', 'Meets all requirements perfectly'],
            ['Minor Shortcoming', '4.5 - 4.9', 'Small improvements needed'],
            ['Shortcoming', '4.0 - 4.4', 'Notable improvements needed'],
            ['Minor Weakness', '3.0 - 3.9', 'Significant improvements needed'],
            ['Weakness', '< 3.0', 'Major improvements required']
        ]
        
        legend_table = Table(legend_data, colWidths=[120, 80, 300])
        legend_styles = [
            (colors.HexColor('#E8F5E9'), colors.HexColor('#2E7D32')),
            (colors.HexColor('#FFF3E0'), colors.HexColor('#E65100')),
            (colors.HexColor('#FFE0B2'), colors.HexColor('#D84315')),
            (colors.HexColor('#FFEBEE'), colors.HexColor('#C62828')),
            (colors.HexColor('#FFCDD2'), colors.HexColor('#B71C1C'))
        ]
        
        legend_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5984')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        for i, (bg_color, text_color) in enumerate(legend_styles, 1):
            legend_table.setStyle(TableStyle([
                ('BACKGROUND', (0, i), (0, i), bg_color),
                ('TEXTCOLOR', (0, i), (0, i), text_color),
            ]))
        
        story.append(legend_table)
        story.append(Spacer(1, 20))

        # Scan Analysis
        for scan in self.evaluation_data:
            story.append(Paragraph(f"Analysis: {scan['scan']}", styles['ReportSubSection']))
            story.append(Paragraph(
                f"Description: {scan.get('description') or 'No available...'}",
                styles['ReportBody']
            ))
            story.append(Paragraph(
                f"Score: {scan['score_scan']}/{scan['max_score_scan']} "
                f"({(scan['score_scan']/scan['max_score_scan']*100):.1f}%)",
                styles['ReportBody']
            ))
            
            # Criteria Table
            if scan.get('criteria'):
                criteria_data = [['Criterion', 'Description', 'Score', 'EU Classification', 'Shortcomings', 'Recommendations']]
                for criterion in scan['criteria']:
                    score = criterion.get('score', 0)
                    max_score = criterion.get('max_score', 5)
                    eu_class = criterion.get('eu_classification', 5)
                    
                    criterion_text = Paragraph(
                        criterion.get('name', ''),
                        ParagraphStyle(
                            'CriterionStyle',
                            parent=styles['TableCell'],
                            wordWrap='CJK',
                            leading=12
                        )
                    )
                    
                    description_text = Paragraph(
                        criterion.get('description', ''),
                        ParagraphStyle(
                            'JustificationStyle',
                            parent=styles['TableCell'],
                            wordWrap='CJK',
                            leading=12
                        )
                    )
                    
                    shortcomings = criterion.get("shortcomings", [])
                    shortcomings_text_value = "<br/>".join([f"• {item}" for item in shortcomings]) if shortcomings else ""

                    shortcoming_text = Paragraph(
                        shortcomings_text_value,
                        ParagraphStyle(
                            'ShortcomingStyle',
                            parent=styles['TableCell'],
                            wordWrap='CJK',
                            leading=12
                        )
                    )

                    recommendations = criterion.get("recommendations", [])
                    recommendations_text_value = "<br/>".join([f"• {item}" for item in recommendations]) if recommendations else ""

                    recommendations_text = Paragraph(
                        recommendations_text_value,
                        ParagraphStyle(
                            'RecommendationsStyle',
                            parent=styles['TableCell'],
                            wordWrap='CJK',
                            leading=12
                        )
                    )

                    criteria_data.append([
                        criterion_text,
                        description_text,
                        f"{score:.1f}/{max_score:.1f}",
                        Paragraph(eu_class, self.get_eu_class_style(eu_class, styles)),
                        shortcoming_text,
                        recommendations_text
                    ])
                
                criteria_table = self.create_criteria_table(criteria_data, styles)
                story.append(criteria_table)
                story.append(Spacer(1, 20))
            
            story.append(PageBreak())

        return story
    
    def build_supporting_evidence(self, styles) -> List:
        """Build the supporting evidence section."""
        story = []
        story.append(Paragraph("4. Supporting Evidence", styles['ReportSection']))

        for scan in self.evaluation_data:
            story.append(Paragraph(f"Evidence for {scan['scan']}", styles['ReportSubSection']))
            
            if scan.get('criteria'):
                for criterion in scan['criteria']:
                    if criterion.get('evidence'):
                        story.append(Paragraph(
                            f"{criterion.get('name', '')} "
                            f"(Score: {criterion.get('score', 0)}/{criterion.get('max_score', 5)})",
                            styles['ReportSubSection']
                        ))
    
                        # Evidence points
                        for ev in criterion['evidence']:
                            story.append(Paragraph(f"• {ev}", styles['ReportBody']))
                    
                    story.append(Spacer(1, 10))
            story.append(Spacer(1, 20))

        return story
    
    def add_page_number(self, canvas, doc) -> None:
        """Add page numbers to the PDF."""
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(740, 25, text)
    
    def generate_pdf_report(self, output_path: str) -> None:
        """Generate a PDF report from the evaluation data."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50,
            allowSplitting=1
        )
        styles = self.get_custom_styles()

        story = []
        story.extend(self.build_first_page(styles))
        story.extend(self.build_executive_summary(styles))
        story.extend(self.build_detailed_analysis(styles))
        story.extend(self.build_supporting_evidence(styles))

        doc.build(story, onFirstPage=self.add_page_number, onLaterPages=self.add_page_number)
        buffer.seek(0)
        
        with open(output_path, "wb") as file:
            file.write(buffer.getvalue())
    
# Example usage           
"""
if __name__ == "__main__":
    input_file = "evaluation.json"
    evaluation_report_path = "evaluation_report.pdf"

    report_manager = ReportManager(input_file)
    report_manager.fill_aditional_data()
    report_manager.generate_pdf_report(evaluation_report_path)
"""