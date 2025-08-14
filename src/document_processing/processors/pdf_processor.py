from langchain_community.document_loaders import PyPDFLoader
from ..document_loader import DocumentLoader
from ..text_splitter import DocumentSplitter

class PDFProcessor(DocumentLoader):
    """Loads and splits PDF"""
    def __init__(self):
        self.splitter = DocumentSplitter()

    def load_document(self, file_path: str):
        pages = PyPDFLoader(file_path).load()
        documents = []
        for page in pages:
            documents.extend(
                self.splitter.split_content(
                    page.page_content,
                    {"source": file_path, "page_number": page.metadata.get("page", 0)+1}
                )
            )
        return documents
