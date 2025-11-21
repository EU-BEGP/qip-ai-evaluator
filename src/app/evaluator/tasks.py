import logging
import requests
import uuid
from celery import shared_task
from django.conf import settings
from pathlib import Path
import sys
from typing import Optional, Dict, List, Callable

sys.path.append(str(Path(__file__).parent.parent.parent.resolve()))

from rag.content_evaluator import ContentEvaluator
from .init_knowledge import build_knowledge_base_auto, load_criteria_auto

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- SHARED WORKER INSTANCES (Runs ONCE per worker start) ---
# This section now correctly matches views.py
logger.info("Initializing shared Celery worker instances...")

# 2. Create the vector_manager ONCE
vector_manager = build_knowledge_base_auto()

# 3. Load the criteria ONCE
criteria_data = load_criteria_auto()

# 4. Create the ContentEvaluator ONCE
evaluator_instance = ContentEvaluator()

# 5. Inject the shared vector_manager into the shared evaluator
evaluator_instance.vector_manager = vector_manager

logger.info("Shared Celery worker instances are ready.")
# --- END OF SHARED SETUP ---

@shared_task(bind=True)
def run_evaluation_task(self, evaluation_id: str, course_key: str, qip_user_id: str, scan_names: Optional[List[str]] = None, previous_evaluation: Optional[Dict] = None, existing_snapshot: Optional[str] = None):
    """
    Celery background task to run a full module evaluation.
    This runs in a separate "worker" process.
    """
    logger.info(f"[{evaluation_id}] Task started for course '{course_key}' and user '{qip_user_id}'.")
    logger.info(f"[{evaluation_id}] Scans to run: {'ALL' if not scan_names else scan_names}")
    if previous_evaluation:
        logger.info(f"[{evaluation_id}] Using previous evaluation data.")

    try:
        # 1. Use the SHARED evaluator instance
        evaluator = evaluator_instance

        # 2. Load module content (uses the evaluator's shared vector_manager)
        docs = evaluator.vector_manager.load_documents([course_key]) # This uses the VM we already set
        if not docs:
            logger.error(f"[{evaluation_id}] No documents found for course_key '{course_key}'.")
            send_callback(evaluation_id, course_key, qip_user_id, status="FAILED", error="No documents found", results=None)
            return

        for i, doc in enumerate(docs):
            doc.metadata["chunk_index"] = i + 1

        evaluator.set_documents_for_rag(docs, existing_snapshot=existing_snapshot)

        if not existing_snapshot and evaluator.document_snapshot:
            send_snapshot_callback(evaluation_id, evaluator.document_snapshot)

        interim_callback_lambda = lambda interim_json: send_interim_callback(
            evaluation_id=evaluation_id,
            interim_json=interim_json
        )

        # 3. Evaluate
        result_json = evaluator.evaluate(
            document_chunks=docs,
            k_doc=10,
            k_kb=5,
            course_key=course_key,
            scan_names=scan_names,
            previous_evaluation=previous_evaluation,
            interim_callback=interim_callback_lambda
        )

        # 4. Evaluation finished, send the FINAL callback
        logger.info(f"[{evaluation_id}] Evaluation complete. Sending FINAL callback...")
        send_callback(evaluation_id, course_key, qip_user_id, status="COMPLETE", results=result_json, error=None)
        
    except Exception as e:
        logger.error(f"[{evaluation_id}] Evaluation task failed: {e}", exc_info=True)
        send_callback(evaluation_id, course_key, qip_user_id, status="FAILED", error=str(e), results=None)

def send_snapshot_callback(evaluation_id: str, snapshot_text: str):
    callback_url = settings.QIP_CALLBACK_URL
    secret_key = settings.QIP_CALLBACK_SECRET
    
    payload = {
        "evaluation_id": evaluation_id,
        "status": "SNAPSHOT_CREATED",
        "snapshot": snapshot_text
    }
    
    headers = {"Content-Type": "application/json", "X-Callback-Secret": secret_key}

    try:
        requests.post(callback_url, json=payload, headers=headers, timeout=5)
        logger.info(f"[{evaluation_id}] Snapshot callback sent.")
    except Exception as e:
        logger.warning(f"[{evaluation_id}] Failed to send snapshot callback: {e}")

def send_interim_callback(evaluation_id: str, interim_json: dict):
    """
    Helper function to POST the full, growing JSON for a single scan.
    """
    callback_url = settings.QIP_CALLBACK_URL
    secret_key = settings.QIP_CALLBACK_SECRET

    payload = {
        "evaluation_id": evaluation_id,
        "status": "CRITERION_COMPLETE",
        "interim_result": interim_json
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Callback-Secret": secret_key
    }

    try:
        requests.post(callback_url, json=payload, headers=headers, timeout=5)
        logger.info(f"[{evaluation_id}] Interim callback sent.")
    
    except requests.exceptions.RequestException as e:
        logger.warning(f"[{evaluation_id}] FAILED to send interim callback: {e}")

def send_callback(evaluation_id: str, course_key: str, qip_user_id: str, status: str, results: Optional[dict], error: Optional[str]):
    """
    Helper function to POST the results back to the QIP client API.
    """
    callback_url = settings.QIP_CALLBACK_URL
    secret_key = settings.QIP_CALLBACK_SECRET

    payload = {
        "evaluation_id": evaluation_id,
        "course_key": course_key,
        "qip_user_id": qip_user_id,
        "status": status,
        "results": results if results else {},
        "error": error if error else ""
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Callback-Secret": secret_key
    }

    try:
        response = requests.post(callback_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status() 
        logger.info(f"[{evaluation_id}] FINAL callback sent successfully to {callback_url}.")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"[{evaluation_id}] FAILED to send FINAL callback to {callback_url}: {e}")
