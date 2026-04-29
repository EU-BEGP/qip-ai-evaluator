# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional
import os
import yaml
from langchain_core.documents import Document

from rag.model_wrapper import get_llm_wrapper
from rag.retrievers.cross_encoder import CrossEncoderRAG
from rag.retrievers.vector_store_manager import VectorStoreManager
from rag.document_processing.metadata_analyzer import MetadataAnalyzer
from .criteria_manager import CriteriaManager
from .metadata_extractor import MetadataExtractorService
from .prompts import build_evaluation_prompt, build_snapshot_prompt

logger = logging.getLogger(__name__)


class ContentEvaluator:
    """Evaluates documents against academic criteria using LLMs with structured JSON output."""

    def __init__(self, cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2",
                 vector_manager=None, rag_model=None):
        """Initialize shared resources and supporting services."""

        self.cfg = self._load_config()

        self.vector_manager = vector_manager or VectorStoreManager()
        self.criteria_manager = CriteriaManager(
            Path(__file__).parents[2] / "config" / "config.yaml"
        )

        self.results: Dict[str, Dict[str, Dict]] = {}
        self.document_chunks: List[Document] = []
        self.document_snapshot = ""

        self.rag = rag_model or CrossEncoderRAG(model_name=cross_encoder_model, use_memory_only=True)
        self.llm = get_llm_wrapper(self.cfg)
        self.metadata_validator = MetadataAnalyzer()

        self._metadata_extractor = MetadataExtractorService(
            cfg=self.cfg,
            vector_manager=self.vector_manager,
            rag=self.rag,
            metadata_validator=self.metadata_validator,
        )

    def _load_config(self) -> Dict:
        """Load YAML configuration and substitute env vars."""

        config_path = Path(__file__).parents[2] / "config" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("${HF_TOKEN}", os.environ.get("HF_TOKEN", ""))
        return yaml.safe_load(content)

    def set_documents_for_rag(self, documents: List[Document],
                               existing_snapshot: Optional[str] = None,
                               generate_snapshot: bool = True) -> None:
        """
        Set documents for CrossEncoderRAG and initialize or reuse an anchored snapshot.
        If existing_snapshot is provided, it is reused directly. Otherwise a new
        digest is generated via LLM unless generate_snapshot is False.
        """

        self.document_chunks = documents
        self.rag.set_documents(documents)

        if existing_snapshot:
            logger.info("Reusing provided document snapshot.")
            self.document_snapshot = existing_snapshot
        elif generate_snapshot:
            logger.info("Generating new document snapshot via LLM...")
            self.document_snapshot = self._build_document_digest_llm()
        else:
            logger.info("Snapshot generation skipped.")
            self.document_snapshot = ""

    def _build_document_digest_llm(self) -> str:
        """
        Create a compact LLM-generated digest using a smart-chunking strategy.
        Selects the first 5 chunks plus the top 15 semantically relevant chunks
        to avoid crashes on large documents while improving accuracy.
        """

        total_chunks_to_use = 20
        first_n_chunks = 5
        top_k_chunks = 15

        if len(self.document_chunks) <= total_chunks_to_use:
            selected_chunks = self.document_chunks
        else:
            first_five = self.document_chunks[:first_n_chunks]
            remaining = self.document_chunks[first_n_chunks:]

            search_query = (
                "Document Title, Abstract, Keywords, "
                "Intended Learning Outcomes, Outline, Table of Contents, Main Headings"
            )
            ranked_remaining = self.rag.rank_chunks(search_query, documents=remaining, top_k=top_k_chunks)
            top_chunks = [doc for doc, _, _ in ranked_remaining]
            top_chunks.sort(key=lambda doc: doc.metadata.get("chunk_index", 0))
            selected_chunks = first_five + top_chunks

        full_text = "\n\n".join(d.page_content for d in selected_chunks)
        return self.llm.run_prompt(build_snapshot_prompt(full_text), mode="snapshot", remember=True)

    def _retrieve_top_document_chunks(self, query: str, k_doc: int) -> List[Document]:
        """Retrieve top-K document chunks via CrossEncoderRAG ranking."""

        ranked = self.rag.rank_chunks(query, top_k=k_doc)
        return [doc for doc, _, _ in ranked]

    def _retrieve_knowledge_base_chunks(self, query: str, top_chunks: List[Document], k_kb: int) -> List[Document]:
        """Retrieve knowledge base chunks via vector similarity, deduplicated against document chunks."""

        kb_candidates = self.vector_manager.retrieve(query, k=k_kb * 2)
        if not kb_candidates:
            return []

        seen_texts = {doc.page_content for doc in top_chunks}
        return [doc for doc in kb_candidates if doc.page_content not in seen_texts][:k_kb]

    def _find_criterion_in_history(self, prev_eval_json: Dict, scan_name: str, criterion_name: str) -> Optional[Dict]:
        """Search a previous evaluation JSON for a specific criterion's data."""

        if not prev_eval_json or "content" not in prev_eval_json:
            return None
        for scan_data in prev_eval_json.get("content", []):
            if scan_data.get("scan") == scan_name:
                for crit_data in scan_data.get("criteria", []):
                    if crit_data.get("name") == criterion_name:
                        return crit_data
        return None

    def _build_previous_eval_section(self, previous_evaluation: Optional[Dict],
                                      scan_name: str, criterion_name: str) -> str:
        """Build the previous evaluation context block for the evaluation prompt."""

        if not (previous_evaluation and scan_name and criterion_name):
            return ""
        prev = self._find_criterion_in_history(previous_evaluation, scan_name, criterion_name)
        if not prev:
            return ""
        return (
            f"### PREVIOUS EVALUATION TO '{criterion_name}' IN THE MODULE (most recent):\n"
            f"Description: {prev.get('description', '')}\n"
            f"Score: {prev.get('score', 0.0)}\n"
            f"Shortcomings: {prev.get('shortcomings', [])}\n"
            f"Recommendations: {prev.get('recommendations', [])}\n\n"
        )

    def _evaluate_criterion(self, criterion: Dict, doc_chunks: List[Document],
                             kb_chunks: List[Document], course_key: str = None,
                             scan_name: str = None, criterion_name: str = None,
                             previous_evaluation: Optional[Dict] = None) -> Dict:
        """Run evaluation for a single criterion and return the result with elapsed time."""

        doc_text = "\n\n".join(d.page_content for d in doc_chunks)
        kb_text = "\n\n".join(d.page_content for d in kb_chunks)
        previous_eval_section = self._build_previous_eval_section(
            previous_evaluation, scan_name, criterion_name
        )
        prompt = build_evaluation_prompt(
            criterion, doc_text, kb_text, self.document_snapshot, previous_eval_section
        )

        start_time = time.time()
        eval_obj = self.llm.run_prompt(prompt, mode="criterion", remember=False)
        return {"evaluation": eval_obj, "elapsed": time.time() - start_time}

    def evaluate(self, document_chunks: List[Document], k_doc: int = 6, k_kb: int = 2,
                 course_key: str = None, scan_names: Optional[List[str]] = None,
                 previous_evaluation: Optional[Dict] = None,
                 interim_callback: Optional[Callable[[dict], None]] = None):
        """
        Evaluate documents against all or selected criteria scans.
        If interim_callback is provided, it is called after each criterion with
        the full, growing JSON for the current scan.
        Returns (result_json, failed_scans_list).
        """

        self.results = {}
        self.document_chunks = document_chunks

        if scan_names:
            scan_name_set = set(scan_names)
            scans_to_process = [s for s in self.criteria_manager.scans if s.get("scan") in scan_name_set]
            if not scans_to_process:
                logger.error(f"Scans '{scan_names}' not found in criteria configuration.")
                return self.generate_json_output(scans_processed=[])
        else:
            scans_to_process = self.criteria_manager.scans

        failed_scans_list = []

        for scan in scans_to_process:
            current_scan_name = scan.get("scan")
            logger.info(f"Starting evaluation for scan: {current_scan_name}")
            scan_failed = False

            for c in scan.get("criteria", []):
                if scan_failed:
                    break

                rubric_description = self.criteria_manager.get_criterion_description(
                    current_scan_name, c["name"]
                )
                crit = {
                    "key": f"{current_scan_name}:{c['name']}",
                    "name": c["name"],
                    "text": self.criteria_manager.get_criterion_text(current_scan_name, c["name"]),
                    "description": rubric_description,
                }

                search_query = f"{crit['name']}: {crit['description']}"
                doc_chunks = self._retrieve_top_document_chunks(search_query, k_doc)
                kb_chunks = self._retrieve_knowledge_base_chunks(search_query, doc_chunks, k_kb)

                max_retries = 3
                attempt = 0
                success = False
                res = None

                while attempt < max_retries and not success:
                    attempt += 1
                    try:
                        res = self._evaluate_criterion(
                            crit, doc_chunks, kb_chunks,
                            course_key, current_scan_name, crit["name"],
                            previous_evaluation=previous_evaluation,
                        )
                        success = True
                    except Exception as e:
                        logger.warning(
                            f"[{course_key}] Criterion '{c['name']}' failed attempt "
                            f"{attempt}/{max_retries}: {e}"
                        )
                        if attempt < max_retries:
                            time.sleep(2)

                if not success:
                    logger.error(f"[{course_key}] Critical failure in scan '{current_scan_name}'.")
                    scan_failed = True
                    failed_scans_list.append(current_scan_name)
                    self.results.pop(current_scan_name, None)
                    break

                if success and res:
                    eval_obj = res["evaluation"]
                    shortcomings_with_deductions = [
                        f"{s} {d:.1f}"
                        for s, d in zip(eval_obj.Shortcomings, eval_obj.Deductions)
                    ]
                    final_score = round(max(0.0, 5.0 + sum(eval_obj.Deductions)), 2)

                    self.results.setdefault(current_scan_name, {})[crit["name"]] = {
                        "description": rubric_description,
                        "llm_response": eval_obj.model_dump_json(indent=2),
                        "retrieved_chunks": [d.page_content for d in doc_chunks + kb_chunks],
                        "score": final_score,
                        "shortcomings": shortcomings_with_deductions,
                        "recommendations": eval_obj.Recommendations,
                        "max_score": 5.0,
                        "elapsed": res["elapsed"],
                    }

                    if interim_callback and not scan_failed:
                        self._fire_interim_callback(
                            interim_callback, scan, current_scan_name, c, course_key
                        )

        return self.generate_json_output(scans_processed=scans_to_process), failed_scans_list

    def _fire_interim_callback(self, interim_callback: Callable, scan: Dict,
                                current_scan_name: str, c: Dict, course_key: str) -> None:
        """Build and fire the interim callback payload for the last completed criterion."""

        try:
            scan_dict = {
                "scan": current_scan_name,
                "description": scan.get("description", ""),
                "criteria": [],
            }
            for crit_in_scan in scan.get("criteria", []):
                crit_name = crit_in_scan.get("name")
                if crit_name in self.results.get(current_scan_name, {}):
                    crit_results = self.results[current_scan_name][crit_name]
                    scan_dict["criteria"].append({
                        "name": crit_name,
                        "description": crit_results.get("description", ""),
                        "score": crit_results.get("score", 0.0),
                        "shortcomings": crit_results.get("shortcomings", []),
                        "recommendations": crit_results.get("recommendations", []),
                        "max_score": 5.0,
                    })

            main_title = (
                self.document_chunks[0].page_content.split("\n")[0]
                if self.document_chunks else "Document Evaluation"
            )
            interim_callback({"title": main_title, "content": [scan_dict]})
            logger.info(f"[{course_key}] Sent interim callback for criterion: {c['name']}")

        except Exception as e:
            logger.error(f"[{course_key}] Interim callback failed: {e}", exc_info=True)

    def generate_json_output(self, scans_processed: Optional[List[Dict]] = None) -> Dict:
        """Generate consolidated JSON output for all processed scans and criteria."""

        main_title = (
            self.document_chunks[0].page_content.split("\n")[0]
            if self.document_chunks else "Document Evaluation"
        )
        content_list = []

        for scan in scans_processed or []:
            scan_name = scan.get("scan")
            if scan_name not in self.results:
                continue
            scan_dict = {
                "scan": scan_name,
                "description": scan.get("description", ""),
                "criteria": [],
            }
            for criterion in scan.get("criteria", []):
                crit_name = criterion.get("name")
                crit_results = self.results.get(scan_name, {}).get(crit_name, {})
                scan_dict["criteria"].append({
                    "name": crit_name,
                    "description": crit_results.get("description", ""),
                    "score": crit_results.get("score", 0.0),
                    "shortcomings": crit_results.get("shortcomings", []),
                    "recommendations": crit_results.get("recommendations", []),
                    "max_score": 5.0,
                })
            content_list.append(scan_dict)

        return {"title": main_title, "content": content_list}

    def extract_metadata(self, course_key: str) -> Dict:
        """Extract structured metadata for a module. Delegates to MetadataExtractorService."""

        return self._metadata_extractor.extract_metadata(course_key)

    def get_module_last_modified(self, course_key: str) -> Optional[str]:
        """Return the module's latest modification date. Delegates to MetadataExtractorService."""

        return self._metadata_extractor.get_module_last_modified(course_key)
