from langchain.document_loaders import Docx2txtLoader
from ..document_loader import DocumentLoader
from ..text_splitter import DocumentSplitter

class DocxProcessor(DocumentLoader):
    """Loads DOCX files and splits into chunks with global chunk_index."""

    def __init__(self):
        self.splitter = DocumentSplitter()

    def load_document(self, file_path: str):
        doc = Docx2txtLoader(file_path).load()[0]
        return self.splitter.split_content(doc.page_content, {"source": file_path}, start_index=0)
