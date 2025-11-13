from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging
import uuid
from pathlib import Path
import sys
import re

sys.path.append(str(Path(__file__).parent.parent.parent.resolve()))

from .tasks import run_evaluation_task
from rag.content_evaluator import ContentEvaluator
base_evaluator = ContentEvaluator()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

@api_view(['POST'])
def evaluate_module(request):
    """
    Endpoint to START an evaluation for a Learnify module.
    This is ASYNCHRONOUS. It returns a task ID immediately.
    
    Request body (example):
    {
        "course_key": "OYJPG",
        "qip_user_id": "user-uuid-12345",
        "scan_names": ["Quality", "Metadata"],
        "previous_evaluation": { ...full results JSON... }
    }
    
    "scan_names" is optional (runs all scans if omitted).
    "previous_evaluation" is optional.
    "qip_user_id" is required.
    """
    course_key = request.data.get("course_key")
    qip_user_id = request.data.get("qip_user_id")
    scan_names = request.data.get("scan_names") # Optional
    previous_evaluation = request.data.get("previous_evaluation") # Optional
    evaluation_id = request.data.get("evaluation_id")

    # --- Validation ---'
    if not course_key:
        return Response(
            {"error": "Missing or invalid 'course_key' in request body"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    if not course_key:
        return Response(
            {"error": "Missing 'course_key' in request body"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    if not qip_user_id:
        return Response(
            {"error": "Missing 'qip_user_id' in request body"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    if scan_names is not None and not isinstance(scan_names, list):
        return Response(
            {"error": "'scan_names' must be a list of strings"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    if previous_evaluation is not None and not isinstance(previous_evaluation, dict):
        return Response(
            {"error": "'previous_evaluation' must be an object (JSON)"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # 1. Generate a unique ID for this specific evaluation run
    logger.info(f"Received evaluation request {evaluation_id} for course '{course_key}' from user '{qip_user_id}'.")

    try:
        last_modified_date = base_evaluator.get_module_last_modified(course_key)
    except Exception as e:
        logger.error(f"Error getting module_last_modified for {course_key}: {e}")
        return Response({"error": "Could not determine module date"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 2. Schedule the background task
    run_evaluation_task.delay(
        evaluation_id=evaluation_id,
        course_key=course_key,
        qip_user_id=qip_user_id,
        scan_names=scan_names,
        previous_evaluation=previous_evaluation
    )

    # 3. Return an "Accepted" response immediately
    return Response(
        {
            "message": "Evaluation has been started.",
            "evaluation_id": evaluation_id,
            "course_key": course_key,
            "last_modified_date": last_modified_date
        },
        status=status.HTTP_202_ACCEPTED
    )

@api_view(['GET'])
def module_last_modified(request):

    course_key = request.query_params.get('course_key')
    if not course_key:
        return Response({"error": "Missing 'course_key' query parameter"}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        mod_date = base_evaluator.get_module_last_modified(course_key)
        return Response({"last_modified_date": mod_date}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error getting module_last_modified for {course_key}: {e}")
        return Response({"error": "Could not determine module date"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
