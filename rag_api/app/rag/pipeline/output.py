# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import Callable, Dict, List, Optional
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

DEFAULT_MAIN_TITLE = "Document Evaluation"
MAX_CRITERION_SCORE = 5.0


def _main_title(document_chunks: List[Document]) -> str:
    """Pick the document's main title from the first chunk, with a sensible fallback."""

    if not document_chunks:
        return DEFAULT_MAIN_TITLE
    return document_chunks[0].page_content.split("\n")[0] or DEFAULT_MAIN_TITLE


def _criterion_payload(crit_name: str, crit_results: Dict) -> Dict:
    """Project per-criterion results into the public payload shape."""

    return {
        "name": crit_name,
        "description": crit_results.get("description", ""),
        "score": crit_results.get("score", 0.0),
        "shortcomings": crit_results.get("shortcomings", []),
        "recommendations": crit_results.get("recommendations", []),
        "max_score": MAX_CRITERION_SCORE,
    }


def build_scan_payload(scan: Dict, current_scan_name: str, results: Dict[str, Dict[str, Dict]]) -> Dict:
    """Build one scan's interim/final payload from accumulated results."""

    scan_dict = {
        "scan": current_scan_name,
        "description": scan.get("description", ""),
        "criteria": [],
    }
    scan_results = results.get(current_scan_name, {})
    for crit_in_scan in scan.get("criteria", []):
        crit_name = crit_in_scan.get("name")
        if crit_name in scan_results:
            scan_dict["criteria"].append(_criterion_payload(crit_name, scan_results[crit_name]))
    return scan_dict


def build_evaluation_output(scans_processed: Optional[List[Dict]], results: Dict[str, Dict[str, Dict]],
                            document_chunks: List[Document]) -> Dict:
    """Build the consolidated JSON output for all processed scans + criteria."""

    content_list: List[Dict] = []
    for scan in scans_processed or []:
        scan_name = scan.get("scan")
        if scan_name not in results:
            continue
        content_list.append(build_scan_payload(scan, scan_name, results))

    return {"title": _main_title(document_chunks), "content": content_list}


def fire_interim_callback(interim_callback: Callable[[dict], None], scan: Dict, current_scan_name: str,
                          results: Dict[str, Dict[str, Dict]], document_chunks: List[Document],
                          course_key: Optional[str], last_criterion_name: Optional[str] = None) -> None:
    """
    Build the interim payload for the current scan and dispatch it. Logs errors
    and swallows them — callback failures must not abort the evaluation loop.
    """

    try:
        scan_dict = build_scan_payload(scan, current_scan_name, results)
        payload = {"title": _main_title(document_chunks), "content": [scan_dict]}
        interim_callback(payload)
        if last_criterion_name:
            logger.info(f"[{course_key}] Sent interim callback for criterion: {last_criterion_name}")
    except Exception as e:
        logger.error(f"[{course_key}] Interim callback failed: {e}", exc_info=True)
