from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging
import uuid
from .tasks import run_evaluation_task
from rag.content_evaluator import ContentEvaluator

base_evaluator = ContentEvaluator()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def extract_learnify_code(input_str):
    """
    Extracts the actual course code (ID) from a full Learnify URL.
    
    Scenarios handled:
    1. "https://time.learnify.se/l/show.html#att/OYJPG" -> "OYJPG"
    2. "https://time.learnify.se/l/show.html#att/OYJPG?lang=en" -> "OYJPG"
    3. "OYJPG" -> "OYJPG"
    """
    if not input_str:
        return None
    
    input_str = input_str.strip()
    
    # 1. Isolate the part after '#att/'
    if "#att/" in input_str:
        code_part = input_str.split("#att/")[-1]
    else:
        code_part = input_str
        
    # 2. Remove query parameters (everything after '?')
    if "?" in code_part:
        code_part = code_part.split("?")[0]
    
    return code_part.strip()

@api_view(['POST'])
def evaluate_module(request):
    """ Endpoint to START an evaluation. """
    # 1. Receive input (Evaluator API sends the FULL LINK)
    course_link_input = request.data.get("course_key")
    qip_user_id = request.data.get("qip_user_id")
    scan_names = request.data.get("scan_names")
    previous_evaluation = request.data.get("previous_evaluation")
    evaluation_id = request.data.get("evaluation_id")
    existing_snapshot = request.data.get("existing_snapshot")

    # --- Validation ---
    if not course_link_input:
        return Response(
            {"error": "Missing 'course_key' (link) in request body"}, 
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

    # 2. Extract the Clean Code (e.g., "OYJPG") exclusively for RAG Logic
    clean_course_code = extract_learnify_code(course_link_input)
    
    # Log using the LINK (Context)
    logger.info(f"Received request {evaluation_id}. Link: '{course_link_input}'. Extracted Code for RAG: '{clean_course_code}'")

    # 3. Check Last Modified
    try:
        last_modified_date = base_evaluator.get_module_last_modified(clean_course_code)
    except Exception as e:
        logger.error(f"Error getting module_last_modified for link '{course_link_input}': {e}")
        return Response({"error": "Could not determine module date (Invalid Link/Code?)"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 4. Schedule the background task
    run_evaluation_task.delay(
        evaluation_id=evaluation_id,
        course_key=clean_course_code,
        qip_user_id=qip_user_id,
        scan_names=scan_names,
        previous_evaluation=previous_evaluation,
        existing_snapshot=existing_snapshot
    )

    # 5. Return Response
    return Response(
        {
            "message": "Evaluation has been started.",
            "evaluation_id": evaluation_id,
            "course_key": course_link_input,
            "last_modified_date": last_modified_date
        },
        status=status.HTTP_202_ACCEPTED
    )

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
