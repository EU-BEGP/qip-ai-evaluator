# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from docling.document_converter import DocumentConverter

from ..document_loader import DocumentLoader
from ..text_splitter import DocumentSplitter


class DoclingProcessor(DocumentLoader):
    """Loads any supported file (PDF, DOCX, PPT, etc.) using Docling and splits into chunks with global chunk_index."""

    def __init__(self):
        self.splitter = DocumentSplitter()
        self.converter = DocumentConverter()

    def convert_to_md(self, file_path: str):
        result = self.converter.convert(file_path)
        return result.document.export_to_markdown()

    def load_document(self, file_path: str):
        md_output = self.convert_to_md(file_path)
        return self.splitter.split_content(md_output, {"source": file_path}, start_index=0)
