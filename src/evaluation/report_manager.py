import json
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.pagesizes import letter
from io import BytesIO

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

####################################################################################

    def get_custom_styles(self):
        """Return a stylesheet with custom styles for the evaluation report"""
        styles = getSampleStyleSheet()

        custom_styles = {
            "ReportTitle": ParagraphStyle(
                name="ReportTitle",
                parent=styles["Heading1"],
                fontSize=24,
                spaceAfter=30,
                alignment=1,  # Center
                textColor=colors.HexColor("#1B365D")  # Dark blue
            ),
            "ReportSection": ParagraphStyle(
                name="ReportSection",
                parent=styles["Heading1"],
                fontSize=16,
                spaceAfter=20,
                spaceBefore=20,
                textColor=colors.HexColor("#2E5984"),  # Professional blue
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
                textColor=colors.HexColor("#444444"),  # Dark gray
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
                textColor=colors.HexColor("#333333")  # Softer black
            ),
            "TableHeader": ParagraphStyle(
                name="TableHeader",
                parent=styles["Normal"],
                fontSize=10,
                leading=12,
                textColor=colors.white,
                alignment=1  # Center
            ),
            "TableCell": ParagraphStyle(
                name="TableCell",
                parent=styles["Normal"],
                fontSize=9,
                leading=12,
                wordWrap="CJK"  # Allow wrapping
            )
        }

        for style_name, style in custom_styles.items():
            styles.add(style)

        return styles

    def build_first_page(self, styles):
        story = []

        #Title Report
        story.append(Paragraph(f"Module Evaluation Report", styles['ReportTitle']))
        story.append(Spacer(1, 30))

        #Table of Contents
        story.append(Paragraph("Table of Contents", styles['ReportSection']))
        toc_data = [
            ["1. Executive Summary"],
            ["2. Detailed Analysis"],
            ["3. Recommendations"],
            ["4. Supporting Evidence"]
        ]
        toc_table = Table(toc_data, colWidths=[400, 50])
        toc_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (-1, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(toc_table)
        story.append(PageBreak())

        return story
    
    def build_executive_summary(self, styles):
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
            
            chart_table = Table(data, colWidths=[200, 70, 70, 80])
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
    
    def add_page_number(self, canvas, doc):
        """Add page numbers to the PDF."""
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(540, 25, text)
    
    def generate_pdf_report(self, output_path: str):
        """Generate a PDF report from the evaluation data."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
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
        #story.extend(build_executive_summary(evaluation, self.styles))
        #story.extend(build_detailed_analysis(evaluation, self.styles))
        #story.extend(build_recommendations(evaluation, self.styles))
        #story.extend(build_supporting_evidence(evaluation, self.styles))

        doc.build(story, onFirstPage=self.add_page_number, onLaterPages=self.add_page_number)
        buffer.seek(0)
        
        with open(output_path, "wb") as file:
            file.write(buffer.getvalue())
    
# Example usage           

if __name__ == "__main__":
    input_file = "evaluation.json"
    evaluation_report_path = "evaluation_report.pdf"

    report_manager = ReportManager(input_file)
    report_manager.fill_aditional_data()
    report_manager.generate_pdf_report(evaluation_report_path)