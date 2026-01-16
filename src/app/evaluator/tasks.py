import logging
import requests
from celery import shared_task
from django.conf import settings
from pathlib import Path
import sys
from typing import Optional, Dict, List

sys.path.append(str(Path(__file__).parent.parent.parent.resolve()))

from rag.content_evaluator import ContentEvaluator
from .init_knowledge import build_knowledge_base_auto, load_criteria_auto
from retrievers.cross_encoder import CrossEncoderRAG

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- SHARED HEAVY RESOURCES (Runs ONCE per worker start) ---
logger.info("Initializing shared AI models (Heavy resources)...")

# 1. Vector Database (Heavy)
GLOBAL_VECTOR_MANAGER = build_knowledge_base_auto()

# 2. Criteria (Lightweight but cached)
load_criteria_auto()

# 3. RAG Neural Network (Very Heavy - PyTorch)
# Load this once globally to share memory across tasks
GLOBAL_RAG_MODEL = CrossEncoderRAG(model_name="cross-encoder/ms-marco-MiniLM-L6-v2", use_memory_only=True)

logger.info("✅ Shared AI models ready.")
# --- END OF SHARED SETUP ---

@shared_task(bind=True)
def run_evaluation_task(self, course_key: str, original_link: str, callback_url: str,
                        evaluation_id: Optional[str] = None, 
                        qip_user_id: Optional[str] = None, 
                        scan_names: Optional[List[str]] = None, 
                        previous_evaluation: Optional[Dict] = None, 
                        existing_snapshot: Optional[str] = None):
    """
    Celery background task to run a full module evaluation.
    This runs in a separate "worker" process.
    """
    log_id = evaluation_id if evaluation_id else "No-ID"
    logger.info(f"[{log_id}] Task started for course '{original_link}'")
    logger.info(f"[{log_id}] Scans to run: {'ALL' if not scan_names else scan_names}")
    if previous_evaluation:
        logger.info(f"[{log_id}] Using previous evaluation data.")

    try:
        # 1 Create evaluator instance
        evaluator = ContentEvaluator(
            vector_manager=GLOBAL_VECTOR_MANAGER,
            rag_model=GLOBAL_RAG_MODEL
        )
        # 2. Load module content (uses the shared vector_manager)
        docs = evaluator.vector_manager.load_documents([course_key])
        if not docs:
            logger.error(f"[{log_id}] No documents found for course_key '{course_key}'.")
            send_callback(callback_url, original_link, "FAILED", error="No documents found", results=None, 
                          evaluation_id=evaluation_id, qip_user_id=qip_user_id)
            return

        for i, doc in enumerate(docs):
            doc.metadata["chunk_index"] = i + 1

        # This modifies only the local 'evaluator' instance state
        evaluator.set_documents_for_rag(docs, existing_snapshot=existing_snapshot)

        # If a NEW snapshot was generated (not provided), send it back immediately
        if not existing_snapshot and evaluator.document_snapshot:
            send_snapshot_callback(callback_url, evaluator.document_snapshot, original_link, evaluation_id, qip_user_id)

        interim_callback_lambda = lambda interim_json: send_interim_callback(
            callback_url=callback_url,
            interim_json=interim_json,
            course_key=original_link,
            evaluation_id=evaluation_id,
            qip_user_id=qip_user_id
        )

        # 3. Evaluate
        result_json, failed_scans = evaluator.evaluate(
            document_chunks=docs,
            k_doc=10,
            k_kb=5,
            course_key=course_key,
            scan_names=scan_names,
            previous_evaluation=previous_evaluation,
            interim_callback=interim_callback_lambda
        )

        # 4. Evaluation finished, send the FINAL callback
        if result_json and result_json.get('content'):
            send_callback(callback_url, original_link, "COMPLETE", results=result_json, error=None, 
                          evaluation_id=evaluation_id, qip_user_id=qip_user_id)
        if failed_scans:
            logger.error(f"Sending FAILED callback for scans: {failed_scans}")
            
            send_callback(
                callback_url, 
                original_link, 
                "FAILED",
                results=None,
                error="Max retries exceeded during processing for Scan",
                evaluation_id=evaluation_id, 
                qip_user_id=qip_user_id,
                scan_names=failed_scans
            )
        
    except Exception as e:
        logger.error(f"[{log_id}] Evaluation task failed: {e}", exc_info=True)
        send_callback(callback_url, original_link, "FAILED", error=str(e), results=None, 
                      evaluation_id=evaluation_id, qip_user_id=qip_user_id)

def build_unified_payload(status: str, course_key: str, result: any, error: Optional[str] = None, 
                          evaluation_id: Optional[str] = None, user_id: Optional[str] = None):
    """ Helper to enforce unified response structure """
    payload = {
        "status": status,
        "result": result if result is not None else {},
        "course_key": course_key
    }
    
    if evaluation_id:
        payload["evaluation_id"] = evaluation_id
    if user_id:
        payload["user_id"] = user_id
    if error:
        payload["error"] = error
        
    return payload

def send_snapshot_callback(callback_url: str, snapshot_text: str, course_key: str, 
                           evaluation_id: Optional[str], qip_user_id: Optional[str]):
    
    secret_key = settings.QIP_CALLBACK_SECRET
    
    payload = build_unified_payload(
        status="SNAPSHOT_CREATED",
        course_key=course_key,
        result=snapshot_text,
        evaluation_id=evaluation_id,
        user_id=qip_user_id
    )
    
    headers = {"Content-Type": "application/json", "X-Callback-Secret": secret_key}

    try:
        requests.post(callback_url, json=payload, headers=headers, timeout=60)
        logger.info(f"[{evaluation_id}] Snapshot callback sent.")
    except Exception as e:
        logger.warning(f"[{evaluation_id}] Failed to send snapshot callback: {e}")

def send_interim_callback(callback_url: str, interim_json: dict, course_key: str,
                          evaluation_id: Optional[str], qip_user_id: Optional[str]):
    
    secret_key = settings.QIP_CALLBACK_SECRET

    payload = build_unified_payload(
        status="CRITERION_COMPLETE",
        course_key=course_key,
        result=interim_json,
        evaluation_id=evaluation_id,
        user_id=qip_user_id
    )
    
    headers = {
        "Content-Type": "application/json",
        "X-Callback-Secret": secret_key
    }

    try:
        requests.post(callback_url, json=payload, headers=headers, timeout=60)
        logger.info(f"[{evaluation_id}] Interim callback sent.")
    
    except requests.exceptions.RequestException as e:
        logger.warning(f"[{evaluation_id}] FAILED to send interim callback: {e}")

def send_callback(callback_url: str, course_key: str, status: str, results: Optional[dict], error: Optional[str],
                  evaluation_id: Optional[str], qip_user_id: Optional[str], scan_names: Optional[List[str]] = None):
    """
    Used for Final COMPLETE or FAILED status
    """
    secret_key = settings.QIP_CALLBACK_SECRET

    payload = build_unified_payload(
        status=status,
        course_key=course_key,
        result=results,
        error=error,
        evaluation_id=evaluation_id,
        user_id=qip_user_id
    )
    
    if scan_names:
        payload["scan_names"] = scan_names
    
    headers = {
        "Content-Type": "application/json",
        "X-Callback-Secret": secret_key
    }

    try:
        response = requests.post(callback_url, json=payload, headers=headers, timeout=60)
        response.raise_for_status() 
        logger.info(f"[{evaluation_id}] FINAL callback sent successfully to {callback_url}.")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"[{evaluation_id}] FAILED to send FINAL callback to {callback_url}: {e}")
