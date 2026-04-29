# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import re

from reportlab.platypus import Paragraph, SimpleDocTemplate
from reportlab.platypus.tableofcontents import TableOfContents


class HyperlinkedTOC(TableOfContents):
    """TOC that renders each entry as a clickable link using the bookmark key."""

    def wrap(self, availWidth, availHeight):
        self._entryData = []
        for entry in getattr(self, "_entries", []):
            if len(entry) == 4:
                level, text, pageNum, key = entry
                link_html = f'<link href="#{key}">{text}</link>'
                para = Paragraph(f"{link_html}{' ' * 4} {pageNum}", self.levelStyles[level])
            else:
                level, text, pageNum = entry
                para = Paragraph(f"{text}{' ' * 4} {pageNum}", self.levelStyles[level])
            self._entryData.append(para)
        return TableOfContents.wrap(self, availWidth, availHeight)


class MyDocTemplate(SimpleDocTemplate):
    """SimpleDocTemplate that registers Section/SubSection headings for the TOC and PDF bookmarks."""

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        try:
            style_name = flowable.style.name
        except Exception:
            return

        if style_name == "Section":
            level = 0
        elif style_name == "SubSection":
            level = 1
        else:
            return

        text = flowable.getPlainText()
        key = re.sub(r"\W+", "_", text)

        try:
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=False)
        except Exception:
            pass

        try:
            self.notify("TOCEntry", (level, text, self.page, key))
        except Exception:
            pass


def add_page_number(canvas, doc) -> None:
    """Draw footer text, page number, and PDF metadata on every page."""

    canvas.setFont("Helvetica", 9)
    canvas.drawString(50, 25, "Evaluation done by EEDA QIP V2.0 Reviewer")
    canvas.drawRightString(560, 25, f"Page {canvas.getPageNumber()}")
    canvas.setAuthor("QIP AI Evaluator")
    canvas.setTitle("AI Evaluation Report")
    canvas.setSubject("Module Evaluation")
