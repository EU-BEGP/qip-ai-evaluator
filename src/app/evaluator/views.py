# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging
import uuid
from .tasks import run_evaluation_task, generate_single_suggestion_task
from rag.content_evaluator import ContentEvaluator

base_evaluator = ContentEvaluator()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def extract_learnify_code(input_str):
    """
    Extracts the actual course code (ID) from a full Learnify URL.
    
    Scenarios handled:
    1. "https://time.learnify.se/l/show.html#att/OYJPG" -> "OYJPG"
    2. "https://time.learnify.se/l/show.html#qx5Ay"     -> "qx5Ay"
    3. "https://time.learnify.se/l/show.html#att/OYJPG?lang=en" -> "OYJPG"
    4. "OYJPG" -> "OYJPG"
    """
    if not input_str:
        return None
    
    input_str = input_str.strip()
    
    # 1. Isolate the fragment (everything after the last '#')
    if "#" in input_str:
        code_part = input_str.split("#")[-1]
    else:
        code_part = input_str
    
    # 2. If it starts with 'att/', remove it (Legacy/Standard links)
    if code_part.startswith("att/"):
        code_part = code_part[4:]
        
    # 3. Remove query parameters (everything after '?')
    if "?" in code_part:
        code_part = code_part.split("?")[0]
    
    # 4. Final cleanup (whitespace and trailing slashes)
    return code_part.strip().strip('/')

@api_view(['POST'])
def evaluate_module(request):
    """ Endpoint to START an evaluation. """
    # 1. Receive input (Evaluator API sends the FULL LINK)
    course_link_input = request.data.get("course_key")
    callback_url = request.data.get("callback_url") # Now Mandatory
    
    # Optional fields
    qip_user_id = request.data.get("qip_user_id")
    evaluation_id = request.data.get("evaluation_id")
    
    scan_names = request.data.get("scan_names")
    previous_evaluation = request.data.get("previous_evaluation")
    existing_snapshot = request.data.get("existing_snapshot")

    # --- Validation ---
    if not course_link_input:
        return Response(
            {"error": "Missing 'course_key' (link) in request body"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    if not callback_url:
        return Response(
            {"error": "Missing 'callback_url' in request body"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    if scan_names is not None and not isinstance(scan_names, list):
        return Response(
            {"error": "'scan_names' must be a list of strings"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # 2. Extract the Clean Code (e.g., "OYJPG") exclusively for RAG Logic
    clean_course_code = extract_learnify_code(course_link_input)
    
    # Log using the LINK (Context)
    logger.info(f"Received request {evaluation_id if evaluation_id else 'No-ID'}. Link: '{course_link_input}'. Extracted Code for RAG: '{clean_course_code}'")

    # 3. Schedule the background task
    run_evaluation_task.delay(
        evaluation_id=evaluation_id,
        course_key=clean_course_code, # Passing clean code for processing
        original_link=course_link_input, # Passing original link for callbacks
        qip_user_id=qip_user_id,
        callback_url=callback_url, # Pass mandatory callback
        scan_names=scan_names,
        previous_evaluation=previous_evaluation,
        existing_snapshot=existing_snapshot
    )

    # 4. Return Response (Unified Standard)
    response_payload = {
        "status": "RECEIVED",
        "result": {}, # Empty for initial receipt
        "course_key": course_link_input
    }
    
    # Optional fields logic
    if evaluation_id:
        response_payload["evaluation_id"] = evaluation_id
    if qip_user_id:
        response_payload["user_id"] = qip_user_id

    return Response(response_payload, status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
def module_last_modified(request):
    """ Checks the last modified date. """
    course_link_input = request.query_params.get('course_key')
    
    if not course_link_input:
        return Response({"error": "Missing 'course_key' query parameter"}, status=status.HTTP_400_BAD_REQUEST)
        
    # Extract code for RAG Logic
    clean_course_code = extract_learnify_code(course_link_input)

    try:
        mod_date = base_evaluator.get_module_last_modified(clean_course_code)
        
        return Response({
            "last_modified_date": mod_date,
            "course_key": course_link_input 
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting module_last_modified for link '{course_link_input}': {e}")
        return Response({"error": "Could not determine module date"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
def get_module_metadata(request):
    """
    Retrieves structured metadata (Abstract, EQF, ELH, etc.) for a given course.
    """
    course_link_input = request.data.get("course_key")
    
    if not course_link_input:
        return Response({"error": "Missing 'course_key'"}, status=status.HTTP_400_BAD_REQUEST)

    clean_course_code = extract_learnify_code(course_link_input)
    
    logger.info(f"Metadata request for: {clean_course_code}")

    try:
        metadata_json = base_evaluator.extract_metadata(clean_course_code)
        
        return Response(metadata_json, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_module_metadata: {e}", exc_info=True)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def get_single_suggestion(request):
    """
    Endpoint to REQUEST a single criterion suggestion asynchronously.
    It returns 202 Accepted immediately. The result is sent to 'callback_url'.
    """
    # 1. Extract Data
    course_link_input = request.data.get("course_key")
    callback_url = request.data.get("callback_url")
    question = request.data.get("review_question")
    description = request.data.get("criteria_description")
    criterion_name = request.data.get("criterion_name")
    qip_user_id = request.data.get("qip_user_id")
    evaluation_id = request.data.get("evaluation_id")

    # 2. Validate Required Fields
    if not all([course_link_input, callback_url, question, description, criterion_name]):
        return Response(
            {"error": "Missing required fields: course_key, callback_url, review_question, criteria_description, or criterion_name"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # 3. Clean Code
    clean_course_code = extract_learnify_code(course_link_input)
    logger.info(f"Queuing suggestion for {clean_course_code} | Criterion: {criterion_name} | Eval ID: {evaluation_id}")

    # 4. Send to Celery
    generate_single_suggestion_task.delay(
        course_key=clean_course_code,
        original_link=course_link_input,
        review_question=question,
        criteria_description=description,
        criterion_name=criterion_name,
        callback_url=callback_url,
        qip_user_id=qip_user_id,
        evaluation_id=evaluation_id
    )

    # 5. Respond
    return Response({
        "status": "RECEIVED",
        "course_key": course_link_input,
        "criterion_name": criterion_name,
        "evaluation_id": evaluation_id
    }, status=status.HTTP_202_ACCEPTED)

@api_view(['POST'])
def validate_module_metadata(request):
    """
    Endpoint to validate metadata presence (Teachers, Keywords, ILOs, Metrics).
    """
    course_link_input = request.data.get("course_key")
    
    if not course_link_input:
        return Response({"error": "Missing 'course_key'"}, status=status.HTTP_400_BAD_REQUEST)
    clean_course_code = extract_learnify_code(course_link_input)
    
    logger.info(f"Metadata Validation request for: {clean_course_code}")

    try:
        validation_results = base_evaluator.validate_metadata(clean_course_code)
        
        return Response(validation_results, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in validate_module_metadata: {e}", exc_info=True)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
