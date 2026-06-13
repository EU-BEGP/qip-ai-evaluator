# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from .extractor import CriteriaExtractor
from .manager import CriteriaManager
from .parsers import DocxCriteriaParser, XlsxCriteriaParser


def create_extractor(input_path: str, output_path: str) -> CriteriaExtractor:
    """Build a CriteriaExtractor with the parser matching input_path's extension."""

    p = input_path.lower()
    if p.endswith(".docx"):
        parser = DocxCriteriaParser(input_path)
    elif p.endswith(".xlsx"):
        parser = XlsxCriteriaParser(input_path)
    else:
        raise ValueError(f"Unsupported criteria file format: {input_path}")
    return CriteriaExtractor(parser, output_path)

