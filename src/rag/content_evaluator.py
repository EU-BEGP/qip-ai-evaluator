from pathlib import Path
import yaml
from typing import List, Dict
from langchain.schema import Document
from langchain_community.llms import Ollama
from langchain_community.vectorstores import Chroma

from .vector_store_manager import VectorStoreManager
from .criteria_manager import CriteriaManager


class ContentEvaluator:
    """Evaluates uploaded documents against criteria using RAG and Ollama Qwen 4B."""

    def __init__(self):
        # Load configuration
        config_path = Path(__file__).parents[1] / "config" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)

        # Initialize managers
        self.vector_manager = VectorStoreManager()  # handles knowledge base
        self.criteria_manager = CriteriaManager(config_path)

        # Initialize LLM
        llm_cfg = self.cfg["llm_settings"]["processing_llm"]
        self.llm = Ollama(
            model=llm_cfg["model"],
            temperature=llm_cfg.get("temperature", 0.2),
            top_p=llm_cfg.get("top_p", 0.9),
        )

        # Placeholder for evaluation results
        self.results: Dict[str, Dict[str, Dict]] = {}

    def _create_temp_vector_store(self, docs: List[Document]) -> Chroma:
        """Create an in-memory vector store for the document being evaluated."""
        return Chroma.from_documents(
            documents=docs,
            embedding=self.vector_manager.embeddings,
            persist_directory=None  # in-memory only
        )

    def evaluate_document(self, scan_name: str, criterion_name: str, document_chunks: List[Document], k: int = 5):
        """
        Evaluate a single criterion for a given scan using:
        - Temporary vector store for the document
        - Main knowledge base vector store for external context
        Prints retrieval steps and multi-query results.
        """
        criterion_text = self.criteria_manager.get_criterion_text(scan_name, criterion_name)
        print(f"\n=== Evaluating Criterion: {criterion_name} for Scan: {scan_name} ===")
        print(f"Criterion text: {criterion_text}\n")

        # Temporary vector store for document
        temp_store = self._create_temp_vector_store(document_chunks)

        # Document retriever
        doc_retriever = temp_store.as_retriever(search_type="mmr", k=k)
        # Multi-query retrieval: you could split the criterion into multiple sub-queries
        doc_queries = [criterion_text]  # for now just one query
        doc_results = [doc_retriever.get_relevant_documents(q) for q in doc_queries]

        print("--- Document Retrieval ---")
        for i, docs_for_query in enumerate(doc_results):
            print(f"Query {i+1}: '{doc_queries[i]}'")
            for j, doc in enumerate(docs_for_query):
                print(f"[{j+1}] {doc.page_content[:100]}...")

        # Knowledge base retriever
        base_retriever = self.vector_manager.create_retriever(search_type="mmr", k=k)
        base_queries = [criterion_text]  # can also use multiple queries
        base_results = [base_retriever.get_relevant_documents(q) for q in base_queries]

        print("\n--- Knowledge Base Retrieval ---")
        for i, docs_for_query in enumerate(base_results):
            print(f"Query {i+1}: '{base_queries[i]}'")
            for j, doc in enumerate(docs_for_query):
                print(f"[{j+1}] {doc.page_content[:100]}...")

        # Combine results (document chunks first, then KB chunks)
        combined_chunks = [doc for docs_for_query in doc_results for doc in docs_for_query] + \
                        [doc for docs_for_query in base_results for doc in docs_for_query]

        print(f"\nTotal combined chunks for prompt: {len(combined_chunks)}")

        # Build LLM prompt
        prompt = self._build_evaluation_prompt(criterion_text, combined_chunks)

        # Query LLM
        response = self.llm.predict(prompt)

        # Store results
        if scan_name not in self.results:
            self.results[scan_name] = {}
        self.results[scan_name][criterion_name] = {
            "llm_response": response,
            "retrieved_chunks": [doc.page_content for doc in combined_chunks]
        }

        print("\n--- Combined Retrieval Chunks (for LLM) ---")
        for i, doc in enumerate(combined_chunks):
            print(f"[{i+1}] {doc.page_content[:100]}...")

        return response

    def _build_evaluation_prompt(self, criterion_text: str, docs: List[Document]) -> str:
        """Construct the evaluation prompt including context from retrieved docs."""
        context_text = "\n\n".join([doc.page_content for doc in docs])
        prompt = (
            "You are an academic evaluator. Evaluate the following content against the criterion below.\n\n"
            f"Criterion:\n{criterion_text}\n\n"
            f"Content:\n{context_text}\n\n"
            "Provide a structured response including:\n"
            "- Score (0-5)\n"
            "- Justification\n"
            "- Evidence from content\n"
            "- Recommendations for improvement\n"
        )
        return prompt

    def evaluate_all(self, document_chunks: List[Document], k: int = 7):
        """Evaluate all criteria for all scans."""
        for scan in self.criteria_manager.scans:
            scan_name = scan.get("scan")
            for criterion in scan.get("criteria", []):
                criterion_name = criterion.get("name")
                print(f"Evaluating '{criterion_name}' in scan '{scan_name}'...")
                self.evaluate_document(scan_name, criterion_name, document_chunks, k=k)
        return self.results

    def get_results(self) -> Dict[str, Dict[str, Dict]]:
        """Return structured evaluation results."""
        return self.results


# ===== Interactive test =====
if __name__ == "__main__":
    evaluator = ContentEvaluator()

    # Step 1: Load knowledge base without touching the documents to evaluate
    print("Loading knowledge base vector store...")
    evaluator.vector_manager.load_vector_store()
    print("Knowledge base loaded.")

    # Step 2: Load document to evaluate (temporary vector store)
    doc_path = input("Enter document file path to evaluate: ").strip()
    docs = evaluator.vector_manager.load_documents([doc_path])
    evaluator.current_document_chunks = docs
    print(f"Loaded {len(docs)} chunks for evaluation (temporary vector store)")

    # Step 3: Interactive criteria evaluation
    print("\nEvaluate criteria (type 'exit' to quit)")
    while True:
        scan_name = input("Enter scan name (or 'exit'): ").strip()
        if scan_name.lower() == "exit":
            break
        criterion_name = input("Enter criterion name: ").strip()

        response = evaluator.evaluate_document(scan_name, criterion_name, evaluator.current_document_chunks, k=5)
        print("\nLLM Evaluation Response:")
        print(response)
