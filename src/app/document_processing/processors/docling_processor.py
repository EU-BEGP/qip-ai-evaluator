# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from docling.document_converter import DocumentConverter
from ..document_loader import DocumentLoader
from ..text_splitter import DocumentSplitter
import os

class DoclingProcessor(DocumentLoader):
    """Loads any supported file (PDF, DOCX, PPT, etc.) using Docling and splits into chunks with global chunk_index."""

    def __init__(self):
        self.splitter = DocumentSplitter()
        self.converter = DocumentConverter()

    def load_document(self, file_path: str):
        result = self.converter.convert(file_path)
        md_output = result.document.export_to_markdown()
        return self.splitter.split_content(md_output, {"source": file_path}, start_index=0)
