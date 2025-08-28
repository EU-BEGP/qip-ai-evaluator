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
        # Use only get_criterion_text; use same for description to avoid missing method errors
        criterion_text = self.criteria_manager.get_criterion_text(scan_name, criterion_name)
        criterion_description = criterion_text  # safe fallback

        print(f"\n=== Evaluating Criterion: {criterion_name} for Scan: {scan_name} ===")
        print(f"Criterion text: {criterion_text}\n")

        temp_store = self._create_temp_vector_store(document_chunks)
        query_variants = self._generate_query_variants(criterion_text, n_variants=3)
        all_doc_queries = [criterion_text] + query_variants

        print("--- Generated Query Variants ---")
        for i, q in enumerate(all_doc_queries):
            print(f"[{i+1}] {q}\n")

        # Document retrieval
        doc_results = self.vector_manager.multi_query_retrieval(all_doc_queries, vector_store=temp_store, k=100, search_type="similarity")
        seen_texts = set()
        scored_chunks = []
        for docs in doc_results:
            for doc in docs:
                if doc.page_content not in seen_texts:
                    seen_texts.add(doc.page_content)
                    scored_chunks.append(doc)

        top_chunks = scored_chunks[:k_doc]
        if len(top_chunks) < k_doc:
            remaining_needed = k_doc - len(top_chunks)
            for doc in document_chunks:
                if doc.page_content not in seen_texts:
                    top_chunks.append(doc)
                    seen_texts.add(doc.page_content)
                    remaining_needed -= 1
                    if remaining_needed == 0:
                        break

        top_chunks.sort(key=lambda d: d.metadata.get("page", 0))
        print(f"--- Document Retrieval (Top {len(top_chunks)} unique) ---")
        for i, doc in enumerate(top_chunks):
            print(f"[{i+1}] {doc.page_content[:100]}...")

        # Knowledge base retrieval
        kb_results = self.vector_manager.multi_query_retrieval([criterion_text], vector_store=self.vector_manager.vector_store, k=k_kb*2)
        seen_texts_kb = set(doc.page_content for doc in top_chunks)
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

        combined_chunks = top_chunks + unique_kb_chunks
        print(f"\nTotal combined chunks for prompt: {len(combined_chunks)}")

        # Build prompt in one line for safety
        prompt = self._build_evaluation_prompt(
            criterion_name, criterion_description, top_chunks, unique_kb_chunks, scan_name=scan_name, scan_description=criterion_description
        )

        response = self.llm.predict(prompt)

        if scan_name not in self.results:
            self.results[scan_name] = {}
        self.results[scan_name][criterion_name] = {
            "llm_response": response,
            "retrieved_chunks": [doc.page_content for doc in combined_chunks]
        }

        return response

    def _build_evaluation_prompt(self, criterion_name: str, criterion_description: str, doc_chunks: List[Document], kb_chunks: List[Document], scan_name: str = None, scan_description: str = None) -> str:
        doc_text = "\n\n".join([doc.page_content for doc in doc_chunks])
        kb_text = "\n\n".join([doc.page_content for doc in kb_chunks])

        return (
            "You are an expert academic evaluator and a meticulous detective.\n\n"
            "### Instructions:\n"
            "1. Carefully analyze the DOCUMENT chunks for any issues, errors, inconsistencies, or ambiguities.\n"
            "2. Extract concrete evidence from the DOCUMENT chunks and use KNOWLEDGE BASE chunks only as reference.\n"
            "3. Assign deductions (negative numbers only, e.g., -0.3) for any shortcomings. Leave array empty if none.\n"
            "4. Always suggest concrete recommendations based on detected issues.\n"
            "5. Base score starts at 5.0. Final score = 5.0 + sum of negative deductions (cannot exceed 5.0 or go below 0.0).\n"
            "6. Output must be valid JSON exactly as specified, including all fields even if empty.\n\n"
            "### JSON Schema:\n"
            "[\n"
            "  {\n"
            f"    \"scan\": \"{scan_name or ''}\",\n"
            f"    \"description\": \"{scan_description or ''}\",\n"
            "    \"criteria\": [\n"
            "      {\n"
            f"        \"name\": \"{criterion_name}\",\n"
            f"        \"description\": \"{criterion_description}\",\n"
            "        \"score\": 5.0,\n"
            "        \"shortcomings\": [],\n"
            "        \"evidence\": [],\n"
            "        \"recommendations\": []\n"
            "      }\n"
            "    ]\n"
            "  }\n"
            "]\n\n"
            "### Criterion to evaluate (check very carefuly if chunks meets the criteria):\n"
            f"{criterion_name}\n\n"
            "### DOCUMENT chunks (primary, to evaluate):\n"
            f"{doc_text}\n\n"
            "### KNOWLEDGE BASE chunks (secondary, reference only):\n"
            f"{kb_text}\n\n"
            "### Output requirements:\n"
            "- Provide only valid JSON.\n"
            "- Score must equal 5.0 plus the sum of negative deductions in 'shortcomings'.\n"
            "- Include all fields ('name', 'description', 'score', 'shortcomings', 'evidence', 'recommendations') even if empty.\n"
            "- Extract concrete evidence from the document chunks to justify deductions.\n"
            "- Provide recommendations whenever a shortcoming is identified.\n"
            "- All deductions must be negative numbers.\n"
            "- The scan field is the same of the criterion name, same as the description, just copy those two.\n"
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
