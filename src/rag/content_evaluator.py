import time
from pathlib import Path
import yaml
from typing import List, Dict
from langchain.schema import Document
from pydantic import BaseModel, Field, ValidationError, model_validator
import json
from ollama import Client

from .vector_store_manager import VectorStoreManager
from .criteria_manager import CriteriaManager
from .cross_encoder import CrossEncoderRAG

# ---- Pydantic Model ----
class CriterionEvaluation(BaseModel):
    """Model for structured criterion evaluation output."""
    Name: str
    Shortcomings: list[str] = Field(..., description="List of shortcomings found, each ending with deduction -x.y")
    Recommendations: list[str] = Field(..., description="List of recommendations, one per shortcoming")
    Deductions: list[float] = Field(..., description="Numeric deductions matching each shortcoming")
    Description: str = Field(..., description="Summary of the overall analysis")

    @model_validator(mode="after")
    def check_lengths(cls, values):
        """Ensure Shortcomings, Recommendations, and Deductions lists have equal lengths."""
        s, r, d = values.Shortcomings, values.Recommendations, values.Deductions
        if not (len(s) == len(r) == len(d)):
            raise ValueError(
                f"Mismatch in lengths: Shortcomings={len(s)}, Recommendations={len(r)}, Deductions={len(d)}"
            )
        return values

class ContentEvaluator:
    """Evaluates documents against academic criteria using LLMs with structured JSON output."""

    def __init__(self, cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"):
        """Initialize evaluator: load config, vector manager, criteria manager, LLM, and CrossEncoderRAG."""
        self.cfg = self._load_config()
        self.vector_manager = VectorStoreManager()
        self.criteria_manager = CriteriaManager(Path(__file__).parents[1] / "config" / "config.yaml")
        self.results: Dict[str, Dict[str, Dict]] = {}
        self.document_chunks: List[Document] = []
        self.rag = CrossEncoderRAG(model_name=cross_encoder_model, use_memory_only=True)
        self.client = Client()

    def _load_config(self) -> Dict:
        """Load YAML configuration for LLM and processing."""
        config_path = Path(__file__).parents[1] / "config" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def set_documents_for_rag(self, documents: List[Document]):
        """Set documents in memory for CrossEncoderRAG reranking."""
        self.document_chunks = documents
        self.rag.set_documents(documents)

    def _retrieve_top_document_chunks(self, query: str, k_doc: int) -> List[Document]:
        """Retrieve top-K document chunks using CrossEncoderRAG ranking without modifying them."""
        ranked = self.rag.rank_chunks(query, top_k=k_doc)
        # Only return the original Document objects, do NOT touch metadata
        return [doc for doc, _, _ in ranked]

    def _retrieve_knowledge_base_chunks(self, query: str, top_chunks: List[Document], k_kb: int) -> List[Document]:
        """Retrieve knowledge base chunks using vector store only (no CrossEncoder)."""
        kb_results = self.vector_manager.multi_query_retrieval(
            [query],
            vector_store=self.vector_manager.vector_store,
            k=k_kb * 2
        )
        seen_texts = set(doc.page_content for doc in top_chunks)
        unique_kb_chunks = []
        for doc in sorted([d for docs in kb_results for d in docs],
                          key=lambda d: d.metadata.get("chunk_index", 0)):
            if doc.page_content not in seen_texts:
                seen_texts.add(doc.page_content)
                unique_kb_chunks.append(doc)
            if len(unique_kb_chunks) >= k_kb:
                break
        return unique_kb_chunks

    def _build_prompt(self, criterion: Dict, doc_chunks: List[Document], kb_chunks: List[Document]) -> str:
        """Build evaluation prompt with DOCUMENT and KNOWLEDGE BASE sections."""
        doc_text = "\n\n".join(d.page_content for d in doc_chunks)
        kb_text = "\n\n".join(d.page_content for d in kb_chunks)

        prompt = (
            "You are an EXPERT AND CONFIDENT academic evaluator.\n"
            "Evaluate the DOCUMENT against the criterion STRICTLY and ONLY using the RUBRIC.\n"
            "Rely on the KNOWLEDGE BASE for additional context if needed.\n"
            "DO NOT BE TOO HARSH, DO NOT TAKE POINTS UNLESS THERE IS A CLEAR REASON AND DO NOT TAKE STRONG DEDUCTIONS.\n"
            "### Instructions:\n"
            "1. Carefully read the CRITERION and the DOCUMENT provided. Search the DOCUMENT for the relevant section for the CRITERION.\n"
            "2. You may consult the KNOWLEDGE BASE for additional context, but primary evaluation should focus on DOCUMENT.\n"
            "3. Start from 5.0 and subtract partial points for shortcomings.\n"
            "4. For EACH Shortcoming:\n"
            "   - Provide exactly ONE Recommendation.\n"
            "   - Provide exactly ONE numeric Deduction.\n"
            "6. Finish with a concise Description summarizing the analysis.\n"
            "7. DO NOT OVERTHINK, ANSWER PRECISE AND QUICKLY.\n"
            "8. ONLY return the following JSON format:\n\n"
            "{\n"
            '  "Name": "<Criterion Name>",\n'
            '  "Shortcomings": ["<shortcoming1>", "<shortcoming2>", ...],\n'
            '  "Recommendations": ["<recommendation1>", "<recommendation2>", ...],\n'
            '  "Deductions": [-x.y, -x.y, ...],\n'
            '  "Description": "<summary of the analysis>"\n'
            "}\n\n"
            f"### Criterion: {json.dumps(criterion, indent=2)}\n\n"
            f"### DOCUMENT:\n{doc_text}\n\n"
            f"### KNOWLEDGE BASE:\n{kb_text}\n\n"
        )
        print("---- Prompt to LLM ----")
        print(prompt)
        return prompt

    def _evaluate_criterion(self, criterion: Dict, doc_chunks: List[Document], kb_chunks: List[Document]):
        """Run evaluation for a single criterion against DOCUMENT and KNOWLEDGE BASE separately."""
        prompt = self._build_prompt(criterion, doc_chunks, kb_chunks)
        start_time = time.time()

        response = self.client.chat(
            model="qwen3:4b",
            messages=[{"role": "user", "content": prompt}],
            format=CriterionEvaluation.model_json_schema(),
            options={"temperature": 0.0},
            think=False,
            stream=False
        )

        elapsed = time.time() - start_time
        full_content = response.message.content

        print(f"---- LLM Response for {criterion['name']} (Elapsed: {elapsed:.2f}s) ----")
        print(full_content)

        try:
            eval_obj = CriterionEvaluation.model_validate_json(full_content)
            return {"evaluation": eval_obj, "elapsed": elapsed}
        except ValidationError as e:
            print(f"Validation error for {criterion['name']}: {e}")
            print("Raw response:", full_content)
            return None

    def evaluate_all(self, document_chunks: List[Document], k_doc: int = 10, k_kb: int = 2):
        """Evaluate all criteria using CrossEncoderRAG for docs and vector store for KB."""
        self.document_chunks = document_chunks
        benchmark_results = []

        for scan in self.criteria_manager.scans:
            scan_name = scan.get("scan")
            criteria = scan.get("criteria", [])

            for c in criteria:
                crit = {
                    "key": f"{scan_name}:{c['name']}",
                    "name": c["name"],
                    "text": self.criteria_manager.get_criterion_text(scan_name, c["name"]),
                    "description": self.criteria_manager.get_criterion_description(scan_name, c["name"])
                }

                search_query = f"{crit['name']}: {crit['description']}"

                # Retrieve top document chunks (CrossEncoderRAG) without touching original chunks
                doc_chunks = self._retrieve_top_document_chunks(search_query, k_doc)

                # Retrieve KB chunks (vector store only)
                kb_chunks = self._retrieve_knowledge_base_chunks(search_query, doc_chunks, k_kb)

                # Evaluate criterion
                res = self._evaluate_criterion(crit, doc_chunks, kb_chunks)
                if res:
                    eval_obj: CriterionEvaluation = res["evaluation"]
                    shortcomings_with_deductions = [
                        f"{s} {d:.1f}" for s, d in zip(eval_obj.Shortcomings, eval_obj.Deductions)
                    ]

                    self.results.setdefault(scan_name, {})[crit["name"]] = {
                        "description": eval_obj.Description,
                        "llm_response": eval_obj.model_dump_json(indent=2),
                        "retrieved_chunks": [d.page_content for d in doc_chunks + kb_chunks],
                        "score": max(0.0, 5.0 + sum(eval_obj.Deductions)),
                        "shortcomings": shortcomings_with_deductions,
                        "recommendations": eval_obj.Recommendations,
                        "max_score": 5.0,
                        "elapsed": res["elapsed"]
                    }
                    benchmark_results.append((crit["name"], res["elapsed"], sum(eval_obj.Deductions)))
        return self.results

    def generate_json_output(self) -> Dict:
        """Generate consolidated JSON output with evaluations for all scans and criteria."""
        main_title = self.document_chunks[0].page_content.split("\n")[0] if self.document_chunks else "Document Evaluation"
        content_list = []

        for scan in self.criteria_manager.scans:
            scan_name = scan.get("scan")
            scan_desc = scan.get("description", "")
            scan_dict = {"scan": scan_name, "description": scan_desc, "criteria": []}

            for criterion in scan.get("criteria", []):
                crit_name = criterion.get("name")
                crit_results = self.results.get(scan_name, {}).get(crit_name, {})
                crit_dict = {
                    "name": crit_name,
                    "description": crit_results.get("description", ""),
                    "score": crit_results.get("score", 0.0),
                    "shortcomings": crit_results.get("shortcomings", []),
                    "recommendations": crit_results.get("recommendations", []),
                    "max_score": 5.0
                }
                scan_dict["criteria"].append(crit_dict)
            content_list.append(scan_dict)

        return {"title": main_title, "content": content_list}
