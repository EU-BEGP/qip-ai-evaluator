import pandas as pd
from pathlib import Path

class CSVCriteriaExtractor:
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

        # Add Scan and Scan Description columns
        data.insert(0, "Scan", "")
        data.insert(1, "Scan Description", "")
        if not data.empty:
            data.at[0, "Scan"] = scan_name
            data.at[0, "Scan Description"] = scan_description

        return data

    def process_file(self) -> None:
        """Read all sheets from an Excel file, combine them, and export as CSV."""
        sheets = pd.read_excel(self.input_file, sheet_name=None, header=None)

        # Process all sheets and filter out empty or invalid ones
        processed = [self.process_sheet(df) for df in sheets.values()]
        combined = pd.concat([df for df in processed if df is not None], ignore_index=True)

        # Export to CSV
        combined.to_csv(self.output_file, index=False, encoding="utf-8-sig")