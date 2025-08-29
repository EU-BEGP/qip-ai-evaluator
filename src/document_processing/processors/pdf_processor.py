from langchain_community.document_loaders import PyPDFLoader
from ..document_loader import DocumentLoader
from ..text_splitter import DocumentSplitter

class PDFProcessor(DocumentLoader):
    """Loads PDF files and splits into chunks with global chunk_index."""

    def __init__(self):
        self.splitter = DocumentSplitter()

    def load_document(self, file_path: str):
        pages = PyPDFLoader(file_path).load()
        all_chunks = []
        current_index = 0
        for page in pages:
            chunks = self.splitter.split_content(
                page.page_content,
                {"source": file_path},
                start_index=current_index
            )
            current_index += len(chunks)
            all_chunks.extend(chunks)
        return all_chunks
