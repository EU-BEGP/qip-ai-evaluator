import re
from pathlib import Path
import yaml
from typing import List, Dict
from langchain.schema import Document
from langchain_community.llms import Ollama
from langchain_community.vectorstores import Chroma

from .vector_store_manager import VectorStoreManager
from .criteria_manager import CriteriaManager


class ContentEvaluator:
    """Evaluates documents against academic criteria using LLMs."""

    def __init__(self):
        self.cfg = self._load_config()
        self.vector_manager = VectorStoreManager()
        self.criteria_manager = CriteriaManager(Path(__file__).parents[1] / "config" / "config.yaml")
        self.llm = self._init_llm()
        self.results: Dict[str, Dict[str, Dict]] = {}

    def _load_config(self) -> Dict:
        config_path = Path(__file__).parents[1] / "config" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _init_llm(self) -> Ollama:
        llm_cfg = self.cfg["llm_settings"]["processing_llm"]
        return Ollama(
            model=llm_cfg["model"],
            temperature=llm_cfg.get("temperature", 0.2),
            top_p=llm_cfg.get("top_p", 0.9)
        )

    def _create_temp_vector_store(self, docs: List[Document]) -> Chroma:
        return self.vector_manager.build_vector_store(docs, persist=False)

    def _retrieve_top_document_chunks(self, query: str, temp_store: Chroma,
                                    document_chunks: List[Document], k_doc: int) -> List[Document]:
        doc_results = self.vector_manager.multi_query_retrieval(
            [query], vector_store=temp_store, k=100, search_type="similarity"
        )
        all_docs = [doc for docs in doc_results for doc in docs]

        seen_texts, scored_chunks = set(), []
        for doc in all_docs:
            if doc.page_content not in seen_texts:
                seen_texts.add(doc.page_content)
                doc.metadata.setdefault("chunk_index", len(scored_chunks) + 1)
                scored_chunks.append(doc)

        # Fill if not enough chunks
        for doc in document_chunks:
            if len(scored_chunks) >= k_doc:
                break
            if doc.page_content not in seen_texts:
                scored_chunks.append(doc)
                seen_texts.add(doc.page_content)

        return sorted(scored_chunks[:k_doc], key=lambda d: d.metadata["chunk_index"])

    def _retrieve_knowledge_base_chunks(self, query: str, top_chunks: List[Document], k_kb: int) -> List[Document]:
        kb_results = self.vector_manager.multi_query_retrieval([query], vector_store=self.vector_manager.vector_store, k=k_kb*2)
        seen_texts = set(doc.page_content for doc in top_chunks)
        unique_kb_chunks = []

        for doc in sorted([d for docs in kb_results for d in docs], key=lambda d: d.metadata.get("chunk_index", 0)):
            if doc.page_content not in seen_texts:
                seen_texts.add(doc.page_content)
                unique_kb_chunks.append(doc)
            if len(unique_kb_chunks) >= k_kb:
                break

        return unique_kb_chunks

    def _build_evaluation_prompt(self, criterion_text: str, doc_chunks: List[Document], kb_chunks: List[Document]) -> str:
        doc_text = "\n\n".join(doc.page_content for doc in doc_chunks)
        kb_text = "\n\n".join(doc.page_content for doc in kb_chunks)
        return (
            "You are an expert academic evaluator.\n"
            "Evaluate the DOCUMENT against the criterion, STRICTLY following the structured JSON format below and according to the rubric.\n"
            "DO NOT include reasoning outside the JSON.\n\n"
            "### Instructions:\n"
            "- Maximum score: 5.0\n"
            "- Deduct points for each shortcoming with negative values (e.g., -0.5)\n"
            "- Evidence MUST NEVER be empty.\n"
            "- Recommendations MUST ALWAYS be included, even if there are no shortcomings.\n"
            "- Return ONLY a valid JSON object with THIS SCHEMA:\n\n"
            "{\n"
            "  \"shortcomings\": [\n"
            "    {\"<description for shorcoming>\": -0.5}\n"
            "  ],\n"
            "  \"evidence\": [\n"
            "    \"<explanatory text justifying the score>\"\n"
            "  ],\n"
            "  \"recommendations\": [\n"
            "    \"<fix recommendation, even if no shortcomings>\"\n"
            "  ]\n"
            "}\n\n"
            "### Criterion:\n"
            f"{criterion_text}\n\n"
            "### DOCUMENT:\n"
            f"{doc_text}\n\n"
            "### KNOWLEDGE BASE (reference only):\n"
            f"{kb_text}\n"
        )

    def evaluate_document(self, scan_name: str, criterion_name: str, document_chunks: List[Document],
                          k_doc: int = 15, k_kb: int = 5):
        criterion_description = self.criteria_manager.get_criterion_description(scan_name, criterion_name)
        criterion_text = self.criteria_manager.get_criterion_text(scan_name, criterion_name)

        temp_store = self._create_temp_vector_store(document_chunks)
        top_chunks = self._retrieve_top_document_chunks(criterion_text, temp_store, document_chunks, k_doc)
        kb_chunks = self._retrieve_knowledge_base_chunks(criterion_text, top_chunks, k_kb)
        combined_chunks = top_chunks + kb_chunks

        prompt = self._build_evaluation_prompt(criterion_text, top_chunks, kb_chunks)
        response = self.llm.invoke(prompt)
        score = self.extract_score(response)

        self.results.setdefault(scan_name, {})[criterion_name] = {
            "description": criterion_description,
            "llm_response": response,
            "retrieved_chunks": [doc.page_content for doc in combined_chunks],
            "score": score
        }
        return response

    def evaluate_all(self, document_chunks: List[Document], k_doc: int = 10, k_kb: int = 5):
        for scan in self.criteria_manager.scans:
            scan_name = scan.get("scan")
            for criterion in scan.get("criteria", []):
                criterion_name = criterion.get("name")
                self.evaluate_document(scan_name, criterion_name, document_chunks, k_doc=k_doc, k_kb=k_kb)
        return self.results

    def extract_score(self, llm_text: str, max_score: float = 5.0) -> float:
        deductions_match = re.search(r"Shortcomings:\n([\s\S]*?)\n\nEvidence:", llm_text)
        total_deduction = 0.0
        if deductions_match:
            lines = deductions_match.group(1).strip().split("\n- ")
            for line in lines:
                match = re.search(r"(-\d*\.?\d+)", line)
                if match:
                    total_deduction += float(match.group(1))
        score = max_score + total_deduction
        return max(0.0, min(score, max_score))

    def eu_classification(self, score: float) -> str:
        if score >= 4.5: return "Excellent"
        if score >= 4.0: return "Very Good"
        if score >= 3.5: return "Good"
        if score >= 3.0: return "Fair"
        return "Poor"

    def generate_json_output(self) -> List[Dict]:
        output = []
        for scan in self.criteria_manager.scans:
            scan_name = scan.get("scan")
            scan_desc = scan.get("description", "")
            scan_dict = {
                "scan": scan_name,
                "description": scan_desc,
                "criteria": []
            }

            for criterion in scan.get("criteria", []):
                crit_name = criterion.get("name")
                crit_results = self.results.get(scan_name, {}).get(crit_name, {})

                llm_response = crit_results.get("llm_response", "")
                score = crit_results.get("score", self.extract_score(llm_response))
                
                # Extraer secciones del LLM response
                shortcomings_match = re.search(r"Shortcomings:\n([\s\S]*?)\n\nEvidence:", llm_response)
                evidence_match = re.search(r"Evidence:\n([\s\S]*?)\n\nRecommendations:", llm_response)
                recommendations_match = re.search(r"Recommendations:\n([\s\S]*)", llm_response)

                shortcomings = [s.strip("- ").strip() for s in shortcomings_match.group(1).split("\n- ")] if shortcomings_match else []
                evidence = evidence_match.group(1).strip() if evidence_match else ""
                recommendations = [r.strip("- ").strip() for r in recommendations_match.group(1).split("\n- ")] if recommendations_match else []

                crit_dict = {
                    "name": crit_name,
                    "description": crit_results.get("description", ""),
                    "score": score,
                    "eu_classification": self.eu_classification(score),
                    "shortcomings": shortcomings,
                    "evidence": evidence,
                    "recommendations": recommendations
                }
                scan_dict["criteria"].append(crit_dict)

            output.append(scan_dict)
        return output

if __name__ == "__main__":
    evaluator = ContentEvaluator()
    print("Loading knowledge base vector store...")
    evaluator.vector_manager.load_vector_store()
    print("Knowledge base loaded.")

    doc_path = input("Enter document file path to evaluate: ").strip()
    docs = evaluator.vector_manager.load_documents([doc_path])

    for i, doc in enumerate(docs):
        doc.metadata["chunk_index"] = i + 1

    evaluator.current_document_chunks = docs
    print(f"Loaded {len(docs)} chunks for evaluation (temporary vector store)")

    # --- Evaluate ALL scans and criteria ---
    print("\nEvaluating all scans and criteria...")
    evaluator.evaluate_all(evaluator.current_document_chunks)

    # --- Generate JSON output ---
    print("\nGenerating JSON output...")
    final_json = evaluator.generate_json_output()
    
    # Print JSON
    import json
    print(json.dumps(final_json, indent=2))

    # Optionally, save JSON to a file
    output_file = "evaluation_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2)
    print(f"\nJSON results saved to {output_file}")
