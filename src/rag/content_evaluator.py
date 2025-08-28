from pathlib import Path
import yaml
from typing import List, Dict
from langchain.schema import Document
from langchain_community.llms import Ollama
from langchain_community.vectorstores import Chroma

from .vector_store_manager import VectorStoreManager
from .criteria_manager import CriteriaManager


class ContentEvaluator:
    def __init__(self):
        config_path = Path(__file__).parents[1] / "config" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)

        self.vector_manager = VectorStoreManager()
        self.criteria_manager = CriteriaManager(config_path)

        llm_cfg = self.cfg["llm_settings"]["processing_llm"]
        self.llm = Ollama(
            model=llm_cfg["model"],
            temperature=llm_cfg.get("temperature", 0.2),
            top_p=llm_cfg.get("top_p", 0.9),
        )

        self.results: Dict[str, Dict[str, Dict]] = {}

    def _create_temp_vector_store(self, docs: List[Document]) -> Chroma:
        return self.vector_manager.build_vector_store(docs, persist=False)

    def _generate_query_variants(self, query: str, n_variants: int = 3) -> List[str]:
        prompt = (
            f"Generate {n_variants} alternative phrasings of the following query. "
            f"Each variant MUST start with '.- ' and be on its own line. "
            f"Do not include explanations, numbering, or extra text.\n\n"
            f"Query: {query}"
        )
        response = self.llm.predict(prompt)
        variants = [
            line.replace(".- ", "").strip()
            for line in response.split("\n")
            if line.strip().startswith(".- ")
        ]
        return variants[:n_variants]

    def evaluate_document(self, scan_name: str, criterion_name: str, document_chunks: List[Document], k_doc: int = 20, k_kb: int = 5):
        criterion_text = self.criteria_manager.get_criterion_text(scan_name, criterion_name)
        print(f"\n=== Evaluating Criterion: {criterion_name} for Scan: {scan_name} ===")
        print(f"Criterion text: {criterion_text}\n")

        temp_store = self._create_temp_vector_store(document_chunks)

        query_variants = self._generate_query_variants(criterion_text, n_variants=3)
        all_doc_queries = [criterion_text] + query_variants

        print("--- Generated Query Variants ---")
        for i, q in enumerate(all_doc_queries):
            print(f"[{i+1}] {q}\n")

        doc_results = self.vector_manager.multi_query_retrieval(
            all_doc_queries,
            vector_store=temp_store,
            k=k_doc * 4,
            search_type="similarity"
        )

        seen_texts = set()
        unique_doc_chunks = []
        for doc in sorted([d for docs in doc_results for d in docs], key=lambda d: d.metadata.get("page", 0)):
            if doc.page_content not in seen_texts:
                seen_texts.add(doc.page_content)
                unique_doc_chunks.append(doc)
            if len(unique_doc_chunks) >= k_doc:
                break

        print(f"--- Document Retrieval (Top {len(unique_doc_chunks)} unique) ---")
        for i, doc in enumerate(unique_doc_chunks):
            print(f"[{i+1}] {doc.page_content[:100]}...")

        kb_results = self.vector_manager.multi_query_retrieval(
            [criterion_text],
            vector_store=self.vector_manager.vector_store,
            k=k_kb * 2
        )

        seen_texts_kb = set(doc.page_content for doc in unique_doc_chunks)
        unique_kb_chunks = []
        for doc in sorted([d for docs in kb_results for d in docs], key=lambda d: d.metadata.get("page", 0)):
            if doc.page_content not in seen_texts_kb:
                seen_texts_kb.add(doc.page_content)
                unique_kb_chunks.append(doc)
            if len(unique_kb_chunks) >= k_kb:
                break

        print(f"\n--- Knowledge Base Retrieval (Top {len(unique_kb_chunks)} unique) ---")
        for i, doc in enumerate(unique_kb_chunks):
            print(f"[{i+1}] {doc.page_content[:100]}...")

        combined_chunks = unique_doc_chunks + unique_kb_chunks
        print(f"\nTotal combined chunks for prompt: {len(combined_chunks)}")

        prompt = self._build_evaluation_prompt(criterion_text, unique_doc_chunks, unique_kb_chunks)
        response = self.llm.predict(prompt)

        if scan_name not in self.results:
            self.results[scan_name] = {}
        self.results[scan_name][criterion_name] = {
            "llm_response": response,
            "retrieved_chunks": [doc.page_content for doc in combined_chunks]
        }

        return response

    def _build_evaluation_prompt(self, criterion_text: str, doc_chunks: List[Document], kb_chunks: List[Document]) -> str:
        doc_text = "\n\n".join([doc.page_content for doc in doc_chunks])
        kb_text = "\n\n".join([doc.page_content for doc in kb_chunks])

        return (
            "You are an academic evaluator.\n\n"
            "Instructions:\n"
            "1. Evaluate ONLY the DOCUMENT chunks (below) against the criterion. "
            "This is the primary content and must be judged for relevance and clarity.\n"
            "2. You may use the KNOWLEDGE BASE chunks (below) only as supporting context. "
            "Do NOT judge them, just use them to enrich your answer.\n\n"
            f"Criterion:\n{criterion_text}\n\n"
            "DOCUMENT chunks (primary, to evaluate):\n"
            f"{doc_text}\n\n"
            "KNOWLEDGE BASE chunks (secondary, for reference only):\n"
            f"{kb_text}\n\n"
            "Provide a structured response including:\n"
            "- Score (0.0-5.5)\n"
            "- Justification\n"
            "- Evidence from document chunks\n"
            "- Recommendations for improvement\n"
        )

    def evaluate_all(self, document_chunks: List[Document], k_doc: int = 20, k_kb: int = 5):
        for scan in self.criteria_manager.scans:
            scan_name = scan.get("scan")
            for criterion in scan.get("criteria", []):
                criterion_name = criterion.get("name")
                print(f"Evaluating '{criterion_name}' in scan '{scan_name}'...")
                self.evaluate_document(scan_name, criterion_name, document_chunks, k_doc=k_doc, k_kb=k_kb)
        return self.results

    def get_results(self) -> Dict[str, Dict[str, Dict]]:
        return self.results


if __name__ == "__main__":
    evaluator = ContentEvaluator()
    print("Loading knowledge base vector store...")
    evaluator.vector_manager.load_vector_store()
    print("Knowledge base loaded.")

    doc_path = input("Enter document file path to evaluate: ").strip()
    docs = evaluator.vector_manager.load_documents([doc_path])
    evaluator.current_document_chunks = docs
    print(f"Loaded {len(docs)} chunks for evaluation (temporary vector store)")

    print("\nEvaluate criteria (type 'exit' to quit)")
    while True:
        scan_name = input("Enter scan name (or 'exit'): ").strip()
        if scan_name.lower() == "exit":
            break
        criterion_name = input("Enter criterion name: ").strip()
        response = evaluator.evaluate_document(scan_name, criterion_name, evaluator.current_document_chunks)
        print("\nLLM Evaluation Response:")
        print(response)
