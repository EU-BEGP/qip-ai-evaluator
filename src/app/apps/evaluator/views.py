# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from rest_framework import generics, status
from rest_framework.response import Response

from rag.rag_pipeline.content_evaluator import ContentEvaluator
from .init_knowledge import build_knowledge_base_auto
from .serializers import (
    EvaluateModuleSerializer,
    ModuleLastModifiedSerializer,
    ModuleMetadataSerializer,
)
from .tasks import run_evaluation_task
from .utils import extract_learnify_code

logger = logging.getLogger(__name__)

# Reuse the vector manager already loaded
_vector_manager = build_knowledge_base_auto()
base_evaluator = ContentEvaluator(vector_manager=_vector_manager)


class EvaluateModuleView(generics.GenericAPIView):
    """Start an asynchronous module evaluation. Returns 202 Accepted immediately."""

    serializer_class = EvaluateModuleSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        clean_course_code = extract_learnify_code(data["course_key"])
        logger.info(
            f"Received request {data['evaluation_id'] or 'No-ID'}. "
            f"Link: '{data['course_key']}'. Code: '{clean_course_code}'"
        )

        run_evaluation_task.delay(
            evaluation_id=data["evaluation_id"],
            course_key=clean_course_code,
            original_link=data["course_key"],
            qip_user_id=data["qip_user_id"],
            callback_url=data["callback_url"],
            scan_names=data["scan_names"],
            previous_evaluation=data["previous_evaluation"],
            existing_snapshot=data["existing_snapshot"],
        )

        response_payload = {
            "status": "RECEIVED",
            "result": {},
            "course_key": data["course_key"],
        }
        if data["evaluation_id"]:
            response_payload["evaluation_id"] = data["evaluation_id"]
        if data["qip_user_id"]:
            response_payload["user_id"] = data["qip_user_id"]

        return Response(response_payload, status=status.HTTP_202_ACCEPTED)


class ModuleLastModifiedView(generics.GenericAPIView):
    """Return the latest modification date for a batch of course keys."""

    serializer_class = ModuleLastModifiedSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course_keys = serializer.validated_data["course_keys"]

        clean_keys = {}
        for key in course_keys:
            try:
                clean_keys[key] = extract_learnify_code(key)
            except Exception as e:
                logger.error(f"Could not parse course key '{key}': {e}")
                clean_keys[key] = None

        valid = {orig: clean for orig, clean in clean_keys.items() if clean}
        invalid = {orig: None for orig, clean in clean_keys.items() if not clean}

        bulk_results = base_evaluator._metadata_extractor.get_bulk_last_modified(
            list(valid.values())
        )
        # Re-map clean key → date back to original key
        clean_to_orig = {v: k for k, v in valid.items()}
        results = {clean_to_orig[clean]: date for clean, date in bulk_results.items()}
        results.update(invalid)

        return Response({"results": results}, status=status.HTTP_200_OK)


class ModuleMetadataView(generics.GenericAPIView):
    """Retrieve structured metadata (Abstract, EQF, ELH, etc.) for a given course."""

    serializer_class = ModuleMetadataSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course_key = serializer.validated_data["course_key"]

        clean_course_code = extract_learnify_code(course_key)
        logger.info(f"Metadata request for: {clean_course_code}")

        try:
            metadata_json = base_evaluator.extract_metadata(clean_course_code)
            return Response(metadata_json, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in ModuleMetadataView: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
