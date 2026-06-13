# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import os
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional
import yaml
from langchain_core.documents import Document

from rag.model_wrapper import get_llm_wrapper
from rag.retrieval import (
    BM25Ranker,
    CrossEncoderReranker,
    KBRetrievalPipeline,
    ModuleRetrievalPipeline,
    RetrievalConfig,
    VectorStore,
    build_kb_pipeline,
    build_module_pipeline,
    count_tokens,
)
from rag.rubric import CriteriaManager
from .batch import build_merged_query, evaluate_batch
from .context.metadata import MetadataExtractorService
from .output import build_evaluation_output, fire_interim_callback
from .context.snapshot import build_module_snapshot

logger = logging.getLogger(__name__)


class ContentEvaluator:
    """Evaluates documents against academic criteria using LLMs with structured JSON output."""

    def __init__(self, cross_encoder_model: Optional[str] = None, vector_store: Optional[VectorStore] = None,
                 kb_bm25: Optional[BM25Ranker] = None, reranker: Optional[CrossEncoderReranker] = None):
        """Initialize shared resources and supporting services."""

        self.cfg = self._load_config()

        self.vector_store = vector_store or VectorStore()
        self.kb_bm25 = kb_bm25
        self.criteria_manager = CriteriaManager(
            Path(__file__).parents[2] / "config" / "config.yaml"
        )

        self.results: Dict[str, Dict[str, Dict]] = {}
        self.document_chunks: List[Document] = []
        self.document_snapshot = ""
        self.doc_embeddings = None  # List[List[float]]
        self._module_pipeline: Optional[ModuleRetrievalPipeline] = None

        ce_model = cross_encoder_model or self.cfg.get("retrieval", {}).get(
            "cross_encoder_model", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
        )
        self.reranker = reranker or CrossEncoderReranker(model_name=ce_model)
        self.llm = get_llm_wrapper(self.cfg)
        self.embeddings = self.vector_store.embeddings

        self._retrieval_cfg = RetrievalConfig.from_dict(self.cfg)
        self._module_token_count: int = 0
        self._criteria_per_call: int = self.cfg.get("llm_settings", {}).get("criteria_per_call", 3)

        # KB retrieval pipeline — built once when KB BM25 is available.
        self._kb_pipeline: Optional[KBRetrievalPipeline] = build_kb_pipeline(
            cfg=self._retrieval_cfg,
            vector_store=self.vector_store,
            kb_bm25=self.kb_bm25,
            reranker=self.reranker,
        )

        self._metadata_extractor = MetadataExtractorService(
            cfg=self.cfg,
            rag=self.reranker,
        )

    def _load_config(self) -> Dict:
        """Load YAML configuration and substitute env vars."""

        config_path = Path(__file__).parents[2] / "config" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("${HF_TOKEN}", os.environ.get("HF_TOKEN", ""))
        return yaml.safe_load(content)

    def set_documents_for_rag(self, documents: List[Document], doc_embeddings=None,
                               existing_snapshot: Optional[str] = None, generate_snapshot: bool = True) -> None:
        """
        Set documents for retrieval. Builds the module-side retrieval pipeline
        (hybrid BM25 + cosine dense + cross-encoder rerank + token-budget select)
        and caches it for reuse across criteria. Reuses existing_snapshot when
        provided; otherwise generates one via LLM.
        """

        self.document_chunks = documents
        self.doc_embeddings = doc_embeddings
        self._module_token_count = count_tokens(documents, self._retrieval_cfg.token_encoding)

        self._module_pipeline = build_module_pipeline(
            cfg=self._retrieval_cfg,
            documents=documents,
            doc_embeddings=doc_embeddings,
            embeddings=self.embeddings,
            reranker=self.reranker,
        )

        budget = self._retrieval_cfg.module_chunk_token_budget
        full_module_mode = self._module_token_count <= budget
        if full_module_mode:
            logger.info(
                f"Full module mode: snapshot suppressed "
                f"({self._module_token_count}/{budget} tokens)."
            )
            self.document_snapshot = ""
        elif existing_snapshot:
            logger.info("Reusing provided document snapshot.")
            self.document_snapshot = existing_snapshot
        elif generate_snapshot:
            logger.info("Generating new document snapshot via LLM...")
            self.document_snapshot = build_module_snapshot(
                documents=self.document_chunks,
                reranker=self.reranker,
                llm=self.llm,
            )
        else:
            logger.info("Snapshot generation skipped.")
            self.document_snapshot = ""

    def _retrieve_top_document_chunks(self, query: str, label: str = "") -> List[Document]:
        """Delegate to the module retrieval pipeline."""

        if self._module_pipeline is None:
            return []
        return self._module_pipeline.retrieve(query, self.document_chunks)

    def _retrieve_knowledge_base_chunks(self, query: str, top_chunks: List[Document],
                                        k_kb: int, label: str = "") -> List[Document]:
        """Delegate to the KB retrieval pipeline."""

        if self._kb_pipeline is None:
            return []
        return self._kb_pipeline.retrieve(query, top_k=k_kb, exclude_docs=top_chunks)

    def evaluate(self, document_chunks: List[Document], k_kb: int = 2, course_key: str = None,
                 scan_names: Optional[List[str]] = None, previous_evaluation: Optional[Dict] = None,
                 interim_callback: Optional[Callable[[dict], None]] = None):
        """
        Evaluate documents against all or selected criteria scans. If
        interim_callback is provided, it is called after each criterion with the
        full, growing JSON for the current scan. Returns (result_json, failed_scans_list).
        """

        self.results = {}
        self.document_chunks = document_chunks

        if scan_names:
            scan_name_set = set(scan_names)
            scans_to_process = [s for s in self.criteria_manager.scans if s.get("scan") in scan_name_set]
            if not scans_to_process:
                logger.error(f"Scans '{scan_names}' not found in criteria configuration.")
                return build_evaluation_output([], self.results, self.document_chunks), []
        else:
            scans_to_process = self.criteria_manager.scans

        failed_scans_list: List[str] = []

        for scan in scans_to_process:
            current_scan_name = scan.get("scan")
            logger.info(f"Starting evaluation for scan: {current_scan_name}")
            scan_succeeded = self._evaluate_scan(
                scan=scan,
                current_scan_name=current_scan_name,
                k_kb=k_kb,
                course_key=course_key,
                previous_evaluation=previous_evaluation,
                interim_callback=interim_callback,
            )
            if not scan_succeeded:
                failed_scans_list.append(current_scan_name)

        return build_evaluation_output(scans_to_process, self.results, self.document_chunks), failed_scans_list

    def _evaluate_scan(self, scan: Dict, current_scan_name: str, k_kb: int, course_key: Optional[str],
                       previous_evaluation: Optional[Dict], interim_callback: Optional[Callable[[dict], None]]) -> bool:
        """
        Evaluate a single scan: batch the scan's criteria, retrieve context, call
        the LLM with retries, and aggregate per-criterion results. Returns True
        on success, False when a batch failed irrecoverably.
        """

        all_criteria = scan.get("criteria", [])
        batches = [
            all_criteria[i:i + self._criteria_per_call]
            for i in range(0, len(all_criteria), self._criteria_per_call)
        ]

        for batch_raw in batches:
            batch = [self._build_criterion_entry(current_scan_name, c) for c in batch_raw]

            merged_query = build_merged_query(batch)
            doc_chunks = self._retrieve_top_document_chunks(merged_query, label=current_scan_name)
            kb_chunks = self._retrieve_knowledge_base_chunks(merged_query, doc_chunks, k_kb, label=current_scan_name)

            batch_results, elapsed = self._run_batch_with_retry(
                batch=batch,
                doc_chunks=doc_chunks,
                kb_chunks=kb_chunks,
                scan_name=current_scan_name,
                course_key=course_key,
                previous_evaluation=previous_evaluation,
            )
            if batch_results is None:
                logger.error(f"[{course_key}] Critical failure in scan '{current_scan_name}'.")
                self.results.pop(current_scan_name, None)
                return False

            per_criterion_elapsed = elapsed / len(batch) if batch else 0.0
            self._record_batch_results(
                batch=batch,
                batch_results=batch_results,
                doc_chunks=doc_chunks,
                kb_chunks=kb_chunks,
                current_scan_name=current_scan_name,
                per_criterion_elapsed=per_criterion_elapsed,
                interim_callback=interim_callback,
                scan=scan,
                course_key=course_key,
            )

        return True

    def _build_criterion_entry(self, scan_name: str, criterion: Dict) -> Dict:
        """Resolve rubric text + description for a single criterion in a batch."""

        rubric_description = self.criteria_manager.get_criterion_description(
            scan_name, criterion["name"]
        ) or "No description."
        return {
            "key": f"{scan_name}:{criterion['name']}",
            "name": criterion["name"],
            "text": self.criteria_manager.get_criterion_text(scan_name, criterion["name"]),
            "description": rubric_description,
        }

    def _run_batch_with_retry(self, batch: List[Dict], doc_chunks: List[Document], kb_chunks: List[Document], scan_name: str,
                              course_key: Optional[str], previous_evaluation: Optional[Dict], max_retries: int = 3) -> tuple:
        """
        Run evaluate_batch with bounded retries. Returns (results, elapsed) on
        success, (None, 0.0) when retries exhausted.
        """

        for attempt in range(1, max_retries + 1):
            try:
                return evaluate_batch(
                    llm=self.llm,
                    batch=batch,
                    doc_chunks=doc_chunks,
                    kb_chunks=kb_chunks,
                    scan_name=scan_name,
                    document_snapshot=self.document_snapshot,
                    previous_evaluation=previous_evaluation,
                    course_key=course_key,
                )
            except Exception as e:
                logger.warning(
                    f"[{course_key}] Batch for scan '{scan_name}' failed attempt "
                    f"{attempt}/{max_retries}: {e}"
                )
                if attempt < max_retries:
                    time.sleep(2)

        return None, 0.0

    def _record_batch_results(self, batch: List[Dict], batch_results: List, doc_chunks: List[Document], kb_chunks: List[Document],
                              current_scan_name: str, per_criterion_elapsed: float, interim_callback: Optional[Callable[[dict], None]], scan: Dict,
                              course_key: Optional[str]) -> None:
        """Apply deductions, persist per-criterion results, fire interim callback."""

        for crit, eval_obj in zip(batch, batch_results):
            total_deduction = sum(abs(d) for d in eval_obj.Deductions)
            final_score = round(max(0.0, 5.0 - total_deduction), 2)

            deductions = [abs(d) for d in eval_obj.Deductions]
            shortcomings_list = []
            for i, s in enumerate(eval_obj.Shortcomings):
                if i < len(deductions) and deductions[i] > 0:
                    shortcomings_list.append(f"{s} -{deductions[i]:.1f}")
                else:
                    shortcomings_list.append(s)

            recommendations_list = list(eval_obj.Recommendations)
            if shortcomings_list and not recommendations_list:
                recommendations_list = ["Review and address the identified shortcomings."]

            self.results.setdefault(current_scan_name, {})[crit["name"]] = {
                "description": crit["description"],
                "llm_response": eval_obj.model_dump_json(indent=2),
                "retrieved_chunks": [d.page_content for d in doc_chunks + kb_chunks],
                "score": final_score,
                "shortcomings": shortcomings_list,
                "recommendations": recommendations_list,
                "max_score": 5.0,
                "elapsed": per_criterion_elapsed,
            }

            if interim_callback:
                fire_interim_callback(
                    interim_callback=interim_callback,
                    scan=scan,
                    current_scan_name=current_scan_name,
                    results=self.results,
                    document_chunks=self.document_chunks,
                    course_key=course_key,
                    last_criterion_name=crit["name"],
                )

    def extract_metadata(self, docs) -> Dict:
        """Extract structured metadata from pre-loaded docs. Delegates to MetadataExtractorService."""

        return self._metadata_extractor.extract_metadata(docs)
