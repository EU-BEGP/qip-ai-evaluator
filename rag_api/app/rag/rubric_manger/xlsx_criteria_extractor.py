# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import pandas as pd
import json
from pathlib import Path


class XLSXCriteriaExtractor:
    """Class to extract, process, and combine Excel sheets into a single CSV file."""

    def __init__(self, input_file: str | Path, output_file: str | Path):
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)

    def extract_table_start(self, df: pd.DataFrame) -> int | None:
        """Find the index of the row containing 'Index' in the first column."""

        match = df[df.iloc[:, 0].astype(str).str.strip().str.lower() == "index"].index
        return match[0] if not match.empty else None

    def extract_scan_metadata(self, df: pd.DataFrame, start_row: int) -> tuple[str, str]:
        """Extract the scan name and description (row above the header)."""

        scan_name = str(df.iloc[start_row - 1, 0]).strip()
        scan_description = str(df.iloc[start_row - 1, 1]).strip()
        return scan_name, scan_description

    def process_sheet(self, df: pd.DataFrame) -> pd.DataFrame | None:
        """Process a single Excel sheet and return a formatted DataFrame."""

        start_row = self.extract_table_start(df)
        if start_row is None:
            return None

        # Read headers and data
        headers = df.iloc[start_row].tolist()
        data = df.iloc[start_row + 1:].reset_index(drop=True)
        data.columns = headers

        # Extract scan metadata
        scan_name, scan_description = self.extract_scan_metadata(df, start_row)

        # Detect metric columns automatically (usually “1” to “5”)
        metric_cols = [col for col in data.columns if str(col).isdigit()]

        # Build criteria list
        criteria_list = []
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

        # Return structured scan object
        return {
            "scan": scan_name,
            "description": scan_description,
            "criteria": criteria_list,
        }

    def process_file(self) -> None:
        """Convert Excel sheets to a structured JSON file."""

        sheets = pd.read_excel(self.input_file, sheet_name=None, header=None)
        scans = []

        for df in sheets.values():
            scan_data = self.process_sheet(df)
            if scan_data:
                scans.append(scan_data)

        # Export JSON
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(scans, f, ensure_ascii=False, indent=4)
        print(f"File '{self.output_file}' generated successfully.")
