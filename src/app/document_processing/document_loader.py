# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
from langchain.schema import Document

class DocumentLoader(ABC):
    """Base class for document loaders"""
    @abstractmethod
    def load_document(self, file_path: str) -> List[Document]:
        pass

class DocumentLoaderFactory:
    """Returns loader based on file extension or special identifiers"""
    @staticmethod
    def create_loader(file_path: str) -> DocumentLoader:
        if "." not in file_path and file_path.isalnum():
            from .processors.learnify_processor import LearnifyProcessor
            return LearnifyProcessor()
        
        # For any file type, DoclingProcessor is used
        from .processors.docling_processor import DoclingProcessor
        return DoclingProcessor()
