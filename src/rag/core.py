# rag/core.py
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

from langchain_community.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document
from langchain_community.chat_models import ChatOllama

# Import our custom processing modules
from document_processing.document_loader import load_document
from document_processing.text_splitter import get_text_splitter
from document_processing.embeddings_manager import EmbeddingsManager

logger = logging.getLogger(__name__)

class RAGEngine:
    """Core RAG engine handling knowledge base, retrieval, and generation"""
    
    def __init__(self):
        # Basic logging setup
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        self.logger = logger
        
        # Load configuration
        self.config = self._load_config()
        
        # Core components
        self.vector_store = None
        self.vector_store_path = Path(self.config["vector_store"]["path"]).resolve()
        
        # Initialize embeddings via our manager
        self.embeddings_manager = EmbeddingsManager(self.config["document_processing"]["embeddings"])
        self.embeddings = self.embeddings_manager.get_embedding_function()
        
        # Initialize LLMs
        self.llm = ChatOllama(**self.config["llm_settings"]["chat_llm"])
        self.processing_llm = ChatOllama(**self.config["llm_settings"]["processing_llm"])
        
        # Session state
        self.current_rubric: Optional[str] = None
        self._referenced_docs: List[Document] = []
        
        self.logger.info("RAG engine initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml"""
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def ingest_document(self, file_path: str) -> bool:
        """Load, split, embed and add document to knowledge base"""
        # Load raw text from file
        text = load_document(file_path)

        # Split into chunks according to config
        splitter = get_text_splitter(self.config["document_processing"]["text_splitter"])
        chunks = splitter.create_documents([text])

        # Add to vector store
        return self.initialize_knowledge_base(chunks)

    def initialize_knowledge_base(self, documents: List[Document]) -> bool:
        """Initialize Chroma vector store with documents"""
        if not documents:
            raise ValueError("Document list is empty")
        
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        self.vector_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=str(self.vector_store_path)
        )
        
        self.qa_chain = self._build_qa_chain()
        return True

    def _build_qa_chain(self) -> ConversationalRetrievalChain:
        """Build QA chain with configurable retrieval"""
        retriever = self.vector_store.as_retriever(
            search_type=self.config.get("retrieval", {}).get("search_type", "mmr"),
            search_kwargs=self.config.get("retrieval", {}).get("search_kwargs", {"k": 5})
        )
        
        return ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            return_source_documents=True
        )

    def set_current_rubric(self, rubric_text: str) -> bool:
        """Set current evaluation rubric"""
        self.current_rubric = rubric_text
        return True

    def get_relevant_chunks(self, query: str, k: int = 5) -> List[Document]:
        """Retrieve relevant document chunks"""
        return self.vector_store.similarity_search(query, k=k)

    def chat_response(self, prompt: str) -> Dict[str, Any]:
        """Generate response using retrieved context"""
        rubric_chunks: List[Document] = []
        rubric_context = ""
        
        # Retrieve rubric context if available
        if self.current_rubric:
            rubric_chunks = self.vector_store.similarity_search(self.current_rubric, k=2)
            rubric_context = "\nRUBRIC CONTEXT:\n" + "\n".join(
                doc.page_content for doc in rubric_chunks
            )
        
        # Retrieve question context
        question_chunks = self.get_relevant_chunks(prompt)
        question_context = "\n".join(doc.page_content for doc in question_chunks)
        
        # Build prompt
        full_prompt = (
            f"CONTEXT:{rubric_context}\n{question_context}\n\n"
            f"QUESTION: {prompt}\n\n"
            f"ANSWER:"
        )
        
        # Generate response
        response = self.llm.invoke(full_prompt).content
        
        # Track referenced docs
        self._referenced_docs.extend(rubric_chunks + question_chunks)
        
        return {
            "response": response,
            "sources": [doc.metadata for doc in rubric_chunks + question_chunks]
        }
