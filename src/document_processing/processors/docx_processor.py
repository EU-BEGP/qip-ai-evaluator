from langchain.document_loaders import Docx2txtLoader
from ..document_loader import DocumentLoader
from ..text_splitter import DocumentSplitter

class DocxProcessor(DocumentLoader):
    """Loads and splits DOCX"""
    def __init__(self):
        self.splitter = DocumentSplitter()

    def load_document(self, file_path: str):
        doc = Docx2txtLoader(file_path).load()[0]
        return self.splitter.split_content(doc.page_content, {"source": file_path})
