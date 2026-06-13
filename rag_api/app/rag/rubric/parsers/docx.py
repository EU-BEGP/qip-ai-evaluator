# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import re
from typing import Dict, List, Optional

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from .base import CriteriaParser

logger = logging.getLogger(__name__)


class DocxCriteriaParser(CriteriaParser):
    """Parse a DOCX rubric file into the standard scans list."""

    def parse(self) -> List[Dict]:
        return self._extract_scans(self.input_path)

    def _normalize_text(self, text: str) -> str:
        """Return the text without extra spaces and leading/trailing whitespace."""

        return " ".join(text.split()).strip()

    def _iter_blocks_in_order(self, doc: Document):
        """Iterate through the document elements in order."""

        for element in doc.element.body.iterchildren():
            if isinstance(element, CT_P):
                yield Paragraph(element, doc)
            elif isinstance(element, CT_Tbl):
                yield Table(element, doc)

    def _parse_scan_heading(self, text: str) -> Optional[str]:
        """Return the name of scan if the line starts with 'SCAN:'."""

        m = re.search(r"SCAN:\s*(.+)", text.strip())
        return self._normalize_text(m.group(1)) if m else None

    def _flush_description(self, current_scan: Dict, buffer: List[str]) -> None:
        """Pass the accumulated text from the buffer to the scan description."""

        if buffer:
            current_scan["description"] = self._normalize_text(" ".join(buffer))
            buffer.clear()

    def _parse_criteria_table(self, table: Table) -> List[Dict]:
        """Parse the criteria in the table."""

        results: List[Dict] = []
        rows = list(table.rows)
        if not rows or len(rows[0].cells) < 9:
            return results

        for row in rows[1:]:
            cells = [self._normalize_text(c.text) for c in row.cells]
            if len(cells) < 9:
                continue

            criterion = {
                "index": cells[0],
                "name": cells[1],
                "description": cells[2],
                "review_question": cells[3],
                "metrics": {
                    "5": cells[4],
                    "4": cells[5],
                    "3": cells[6],
                    "2": cells[7],
                    "1": cells[8],
                },
            }

            if criterion["name"]:
                results.append(criterion)
        return results

    def _extract_scans(self, docx_path: str) -> List[Dict]:
        """
        Extracts SCAN blocks from a DOCX with:
        - A paragraph header: 'SCAN: Name...'
        - Description in following paragraphs (until a table or the next SCAN is found)
        - Criteria table
        """

        doc = Document(docx_path)
        scans: List[Dict] = []
        current_scan: Optional[Dict] = None
        desc_buffer: List[str] = []

        for block in self._iter_blocks_in_order(doc):
            if isinstance(block, Paragraph):
                text = self._normalize_text(block.text)
                if not text:
                    continue

                maybe_scan = self._parse_scan_heading(text)
                if maybe_scan is not None:
                    if current_scan:
                        self._flush_description(current_scan, desc_buffer)
                        scans.append(current_scan)
                    current_scan = {"scan": maybe_scan, "description": "", "criteria": []}
                else:
                    if current_scan:
                        desc_buffer.append(text)

            elif isinstance(block, Table):
                if current_scan:
                    self._flush_description(current_scan, desc_buffer)
                    current_scan["criteria"].extend(self._parse_criteria_table(block))

        if current_scan:
            self._flush_description(current_scan, desc_buffer)
            scans.append(current_scan)

        return scans
