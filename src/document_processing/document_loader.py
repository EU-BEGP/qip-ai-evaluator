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
        
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            from .processors.pdf_processor import PDFProcessor
            return PDFProcessor()
        elif ext == ".txt":
            from .processors.text_processor import TextProcessor
            return TextProcessor()
        elif ext == ".docx":
            from .processors.docx_processor import DocxProcessor
            return DocxProcessor()
        else:
            raise ValueError(f"Unsupported file type: {ext}. Use course key (e.g., 'OYJPG') for Learnify API.")
