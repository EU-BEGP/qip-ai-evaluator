# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import json
import logging

from .parsers.base import CriteriaParser

logger = logging.getLogger(__name__)


class CriteriaExtractor:
    """Drives the parse → JSON pipeline for any CriteriaParser implementation."""

    def __init__(self, parser: CriteriaParser, output_path: str):
        self.parser = parser
        self.output_path = output_path

    def process_file(self) -> None:
        try:
            scans = self.parser.parse()
            self._save_json(scans)
            logger.info(f"Extracted {len(scans)} scan(s) from {self.parser.input_path} to {self.output_path}")
        except Exception as e:
            logger.error(f"Failed to extract criteria from '{self.parser.input_path}': {e}", exc_info=True)
            raise

    def _save_json(self, scans) -> None:
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(scans, f, indent=4, ensure_ascii=False)
