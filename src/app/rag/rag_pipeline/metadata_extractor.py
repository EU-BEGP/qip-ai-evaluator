# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import concurrent.futures
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from langchain_core.documents import Document

from .prompts import build_eqf_prompt, build_metadata_prompt

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MetadataExtractorService:
    """Handles metadata extraction and module last-modified queries."""

    def __init__(self, cfg: Dict, vector_manager, rag, metadata_validator):
        """Initialize with shared resources from ContentEvaluator."""

        self.cfg = cfg
        self.vector_manager = vector_manager
        self.rag = rag
        self.metadata_validator = metadata_validator

    def _resolve_project_path(self, path_str: str) -> Path:
        """Resolve a config path relative to the project root."""

        path = Path(path_str)
        if path.is_absolute():
            return path
        return (PROJECT_ROOT / path).resolve()

    def _get_extended_metadata_context(self, docs: List[Document], n_relevant: int = 5) -> Tuple[str, int]:
        """
        Build context text from the Module section and top semantic chunks.
        Returns (context_text, module_start_idx). module_start_idx is -1 when
        no Module/Chapter section was found.
        """

        if not docs:
            return "", -1

        metadata_text, start_idx = self.metadata_validator._get_target_context(docs)
        query = (
            "Teachers Authors Keywords Intended Learning Outcomes "
            "Expected Learning Hours Abstract Societal Relevance"
        )
        ranked = self.rag.rank_chunks(query, documents=docs, top_k=n_relevant * 3)
        final_pieces = []

        first_chunk_text = docs[0].page_content.strip()

        if metadata_text and first_chunk_text in metadata_text:
            final_pieces.append("Module Metadata >\n" + metadata_text.strip())
        else:
            final_pieces.append("Document Title / Header >\n" + first_chunk_text)
            if metadata_text:
                final_pieces.append("\nModule Metadata >\n" + metadata_text.strip())

        final_pieces.append("\nExtra Relevant Chunks >")
        added = 0
        for doc, _, _ in ranked:
            if added >= n_relevant:
                break
            chunk_text = doc.page_content.strip()
            check_snippet = chunk_text[:60]
            if chunk_text != first_chunk_text and (
                not metadata_text or check_snippet not in metadata_text
            ):
                final_pieces.append(f"- {chunk_text}")
                added += 1

        return "\n\n".join(final_pieces), start_idx

    def extract_metadata(self, course_key: str) -> Dict:
        """
        Extract structured module metadata using a 2-step AI process.
        Step 1 extracts basic fields (title, abstract, ELH, EQF, etc.).
        Step 2 assigns EQF levels to individual ILOs using the EQF guideline.
        """

        docs = self.vector_manager.load_documents([course_key])
        eqf_guideline_text = self._load_eqf_guideline()

        if not docs:
            logger.error(f"No documents found for {course_key}")
            return self._empty_metadata_error()

        context_text, start_idx = self._get_extended_metadata_context(docs, n_relevant=5)

        if start_idx == -1:
            logger.warning("No Module Section found. AI will rely purely on top semantic chunks.")
        else:
            logger.info("Extracting AI metadata using Target Block + Top 5 semantic chunks.")

        try:
            from rag.model_wrapper import get_llm_wrapper

            llm = get_llm_wrapper(self.cfg)
            res_basic_raw = llm.run_prompt(build_metadata_prompt(context_text), mode=None, remember=False)
            res_eqf_raw = llm.run_prompt(build_eqf_prompt(context_text, eqf_guideline_text), mode=None, remember=False)

            data_basic = self._parse_llm_json(res_basic_raw)
            data_eqf_full = self._parse_llm_json(res_eqf_raw)

            data_eqf_clean = {
                "suggested_knowledge": data_eqf_full.get("suggested_knowledge", "N/A"),
                "suggested_skills": data_eqf_full.get("suggested_skills", "N/A"),
                "suggested_ra": data_eqf_full.get("suggested_ra", "N/A"),
            }

            final_metadata = {**data_basic, **data_eqf_clean}
            expected_keys = [
                "title", "abstract", "uniqueness", "societal_relevance", "elh",
                "eqf", "smcts", "teachers", "keywords", "suggested_knowledge",
                "suggested_skills", "suggested_ra",
            ]
            for key in expected_keys:
                if key not in final_metadata:
                    final_metadata[key] = "N/A"

            return final_metadata

        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return self._empty_metadata_error()

    def get_module_last_modified(self, course_key: str,
                                  session: Optional[requests.Session] = None) -> Optional[str]:
        """
        Return the latest modification date of the module by querying the Learnify API.
        Compares the root page, the Module/Chapter page, and its nested pages.
        Accepts an optional shared session for connection reuse in bulk calls.
        """

        structure_url = f"https://time.learnify.se/learnifyer/api/2/page/0?key={course_key}"
        logger.info(f"Fetching module modified date for key: {course_key}")
        requester = session or requests

        try:
            response = requester.get(structure_url, timeout=15)
            response.raise_for_status()

            root_data = response.json()
            module_page = next(
                (
                    p for p in root_data.get("pages", [])
                    if p.get("pageType") == 8
                    and p.get("title", "").strip().lower() in ["module", "chapter"]
                ),
                None,
            )

            if not module_page:
                logger.warning(f"API response for {course_key}: 'Module/Chapter' page (type 8) not found.")
                return None

            dates = []
            if root_data.get("modified"):
                dates.append(root_data["modified"])
            if module_page.get("modified"):
                dates.append(module_page["modified"])
            dates.extend(p["modified"] for p in module_page.get("pages", []) if p.get("modified"))

            return max(dates) if dates else None

        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to load structure for {course_key}: HTTP {e.response.status_code}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to load structure for {course_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_module_last_modified: {e}")
            return None

    def get_bulk_last_modified(self, course_keys: List[str],
                                max_workers: int = 20) -> Dict[str, Optional[str]]:
        """
        Fetch last-modified dates for multiple course keys in parallel.
        Uses a shared connection-pooled session and a thread pool.
        Returns dict mapping original course_key → date string or None.
        """

        adapter = HTTPAdapter(
            pool_connections=max_workers,
            pool_maxsize=max_workers,
            max_retries=Retry(total=2, backoff_factor=0.3),
        )
        results: Dict[str, Optional[str]] = {}

        with requests.Session() as session:
            session.mount("https://", adapter)
            workers = min(max_workers, len(course_keys))

            def fetch(key: str):
                return key, self.get_module_last_modified(key, session=session)

            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                for key, date in executor.map(fetch, course_keys):
                    results[key] = date

        return results

    def _load_eqf_guideline(self) -> str:
        """Load the EQF levels guideline text from the knowledge base directory."""

        kb_dir_cfg = self.cfg.get("knowledge", {}).get("kb_dir")
        if not kb_dir_cfg:
            raise ValueError("Missing 'knowledge.kb_dir' in config.yaml")

        kb_dir = self._resolve_project_path(kb_dir_cfg)
        if not kb_dir.exists():
            logger.warning(f"KB directory {kb_dir} does not exist. Creating it...")
            kb_dir.mkdir(parents=True, exist_ok=True)
            return ""

        eqf_file = next(
            (
                str(p) for p in kb_dir.iterdir()
                if p.is_file() and p.stem == "EQF_Levels" and p.suffix.lower() in [".md", ".txt"]
            ),
            None,
        )

        if eqf_file:
            with open(eqf_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    @staticmethod
    def _parse_llm_json(raw_text: str) -> Dict:
        """Strip markdown fences and parse JSON from LLM output."""

        clean = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)

    @staticmethod
    def _empty_metadata_error() -> Dict:
        """Return a safe default when metadata extraction fails."""
        
        return {
            "title": "Error extracting metadata", "abstract": "", "uniqueness": "",
            "societal_relevance": "", "elh": "", "eqf": "", "smcts": "",
            "teachers": "", "keywords": "", "suggested_knowledge": "",
            "suggested_skills": "", "suggested_ra": "",
        }
