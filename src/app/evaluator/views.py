# Src/app/evaluator/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
import logging
from pathlib import Path
import sys

# -------------------- FIX PATHS --------------------
# Add project root so imports work
sys.path.append(str(Path(__file__).parent.parent.parent.resolve()))

from rag.content_evaluator import ContentEvaluator
from database.database_manager import DatabaseManager
from .init_knowledge import build_knowledge_base_auto, load_criteria_auto

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# -------------------- AUTO LOAD KB AND CRITERIA --------------------
vector_manager = build_knowledge_base_auto()
criteria_data = load_criteria_auto()

# -------------------- API ENDPOINT --------------------
@api_view(['POST'])
def evaluate_module(request):
    """
    Endpoint to evaluate a Learnify module.
    Request body: {"course_key": "OYJPG"}
    Returns: evaluation JSON
    """
    course_key = request.data.get("course_key")
    if not course_key:
        return Response({"error": "Missing 'course_key' in request body"}, status=400)

    # Create evaluator
    db_manager = DatabaseManager()
    evaluator = ContentEvaluator(database_manager=db_manager)
    evaluator.vector_manager = vector_manager

    # Load module content
    docs = vector_manager.load_documents([course_key])
    for i, doc in enumerate(docs):
        doc.metadata["chunk_index"] = i + 1

    evaluator.current_document_chunks = docs
    evaluator.set_documents_for_rag(docs)

    # Evaluate
    evaluator.evaluate_all(document_chunks=docs, k_doc=10, k_kb=5, course_key=course_key)
    result_json = evaluator.generate_json_output()

    return Response(result_json)
