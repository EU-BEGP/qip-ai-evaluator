# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import Dict, List, Optional, Tuple
import pandas as pd

from .base import CriteriaParser


class XlsxCriteriaParser(CriteriaParser):
    """Parse an XLSX rubric file into the standard scans list."""

    def parse(self) -> List[Dict]:
        sheets = pd.read_excel(self.input_path, sheet_name=None, header=None)
        scans: List[Dict] = []
        for df in sheets.values():
            scan = self._process_sheet(df)
            if scan:
                scans.append(scan)
        return scans

    def _extract_table_start(self, df: pd.DataFrame) -> Optional[int]:
        """Find the index of the row containing 'Index' in the first column."""

        match = df[df.iloc[:, 0].astype(str).str.strip().str.lower() == "index"].index
        return match[0] if not match.empty else None

    def _extract_scan_metadata(self, df: pd.DataFrame, start_row: int) -> Tuple[str, str]:
        """Extract the scan name and description (row above the header)."""

        scan_name = str(df.iloc[start_row - 1, 0]).strip()
        scan_description = str(df.iloc[start_row - 1, 1]).strip()
        return scan_name, scan_description

    def _process_sheet(self, df: pd.DataFrame) -> Optional[Dict]:
        """Process a single Excel sheet and return a formatted scan dict."""

        start_row = self._extract_table_start(df)
        if start_row is None:
            return None

        headers = df.iloc[start_row].tolist()
        data = df.iloc[start_row + 1:].reset_index(drop=True)
        data.columns = headers

        scan_name, scan_description = self._extract_scan_metadata(df, start_row)

        # Detect metric columns automatically (usually "1" to "5")
        metric_cols = [col for col in data.columns if str(col).isdigit()]

        criteria_list: List[Dict] = []
        for _, row in data.iterrows():
            metrics = {str(k): str(row[k]).strip() for k in metric_cols if pd.notna(row[k])}
            criteria = {
                "index": str(row["Index"]).strip(),
                "name": str(row["Criterion"]).strip(),
                "description": str(row["Description"]).strip(),
                "review_question": str(row["Review Question"]).strip(),
                "metrics": metrics,
            }
            criteria_list.append(criteria)

        return {
            "scan": scan_name,
            "description": scan_description,
            "criteria": criteria_list,
        }
