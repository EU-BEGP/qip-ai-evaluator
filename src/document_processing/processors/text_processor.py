from langchain.document_loaders import TextLoader
from ..document_loader import DocumentLoader
from ..text_splitter import DocumentSplitter

class TextProcessor(DocumentLoader):
    """Loads and splits TXT"""
    def __init__(self):
        self.splitter = DocumentSplitter()

    def load_document(self, file_path: str):
        doc = TextLoader(file_path, encoding="utf-8", autodetect_encoding=True).load()[0]
        return self.splitter.split_content(doc.page_content, {"source": file_path})
