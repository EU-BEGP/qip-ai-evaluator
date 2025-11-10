from rest_framework.decorators import api_view
from rest_framework.response import Response
import logging
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent.resolve()))

from rag.content_evaluator import ContentEvaluator
from .init_knowledge import build_knowledge_base_auto, load_criteria_auto
from .models import Module, Evaluation

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
    evaluator = ContentEvaluator()
    evaluator.vector_manager = vector_manager

    # Load module content
    docs = vector_manager.load_documents([course_key])
    for i, doc in enumerate(docs):
        doc.metadata["chunk_index"] = i + 1

    evaluator.current_document_chunks = docs
    evaluator.set_documents_for_rag(docs)

    # Evaluate
    evaluator.evaluate(document_chunks=docs, k_doc=10, k_kb=5, course_key=course_key)
    result_json = evaluator.generate_json_output()

    return Response(result_json)

@api_view(['GET'])
def list_evaluations(request, course_key):
    """
    Endpoint to list the last 3 evaluations for a module.
    Returns a light-weight list (ID and date) for a dropdown.
    """
    try:
        # 1. Ensure the module exists
        Module.objects.get(pk=course_key)
    except Module.DoesNotExist:
        return Response({"error": "Module not found"}, status=404)

    # 2. Get the last 3 evaluations for this module, ordered by date
    evaluations = Evaluation.objects.filter(
        module__course_key=course_key
    ).order_by('-evaluation_date')[:3]

    # 3. Prepare the light-weight data for the frontend
    data = [
        {
            "id": ev.id,  # The unique ID of the evaluation
            "date": ev.formatted_date # Using your @property from the model
        }
        for ev in evaluations
    ]

    return Response(data)

@api_view(['GET'])
def get_evaluation_detail(request, pk):
    """
    Endpoint to get the full JSON results for a specific
    evaluation by its unique ID (pk).
    """
    try:
        # 1. Find the evaluation by its primary key (id)
        evaluation = Evaluation.objects.get(pk=pk)
    except Evaluation.DoesNotExist:
        return Response({"error": "Evaluation not found"}, status=404)

    # 2. Use your model's method to get the JSON as a dict
    results_dict = evaluation.get_results_dict()

    return Response(results_dict)
