# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from abc import ABC, abstractmethod
from typing import Dict, List


class CriteriaParser(ABC):
    """Parses a source rubric file into the standard scans list."""

    def __init__(self, input_path: str):
        self.input_path = input_path

    @abstractmethod
    def parse(self) -> List[Dict]:
        """
        Return a list of scan dicts:
        [{'scan': str, 'description': str, 'criteria': [{...}, ...]}, ...]
        """
