# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from rest_framework import generics, status
from rest_framework.response import Response

from rag.pipeline.evaluator import ContentEvaluator
from rag.document_processing.processors.learnify import LearnifyUnavailableError
from rag.document_processing.processors.learnify.client import fetch_module_last_modified
from .caching import acquire_last_modified, acquire_metadata
from .bootstrap import build_knowledge_base_auto
from .serializers import (
    CancelEvaluationSerializer,
    EvaluateModuleSerializer,
    ModuleLastModifiedSerializer,
    ModuleMetadataSerializer,
)
from .tasks import mark_cancelled, run_evaluation_task
from .utils import extract_learnify_code

logger = logging.getLogger(__name__)

# Reuse the vector store + KB BM25
_vector_store, _kb_bm25 = build_knowledge_base_auto()
base_evaluator = ContentEvaluator(vector_store=_vector_store, kb_bm25=_kb_bm25)


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
            run_id=data["run_id"],
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


class CancelEvaluationView(generics.GenericAPIView):
    """Set a cancel flag for a running evaluation task identified by run_id."""

    serializer_class = CancelEvaluationSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run_id = serializer.validated_data["run_id"]

        mark_cancelled(run_id)
        logger.info(f"Cancel flag set for run_id={run_id}")

        return Response({"status": "CANCEL_REQUESTED", "run_id": run_id}, status=status.HTTP_200_OK)


class ModuleLastModifiedView(generics.GenericAPIView):
    """Return the latest modification date for a batch of course keys."""

    serializer_class = ModuleLastModifiedSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course_keys = serializer.validated_data["course_keys"]
        force = serializer.validated_data["force"]

        clean_keys = {}
        for key in course_keys:
            try:
                clean_keys[key] = extract_learnify_code(key)
            except Exception as e:
                logger.error(f"Could not parse course key '{key}': {e}")
                clean_keys[key] = None

        valid = {orig: clean for orig, clean in clean_keys.items() if clean}
        results = {orig: None for orig, clean in clean_keys.items() if not clean}

        def resolve(orig, clean):
            return orig, acquire_last_modified(
                clean,
                lambda: fetch_module_last_modified(clean),
                force=force,
            )

        try:
            if valid:
                workers = min(20, len(valid))
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = [executor.submit(resolve, orig, clean) for orig, clean in valid.items()]
                    for future in as_completed(futures):
                        orig, date = future.result()
                        results[orig] = date
        except LearnifyUnavailableError as e:
            logger.error(f"Learnify unavailable during last_modified fetch: {e}")
            return Response(
                {"error": "Content service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

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
            last_mod = acquire_last_modified(
                clean_course_code,
                lambda: fetch_module_last_modified(clean_course_code),
            )
        except LearnifyUnavailableError as e:
            logger.error(f"Learnify unavailable during metadata request: {e}")
            return Response(
                {"error": "Content service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not last_mod:
            return Response(
                {"error": "Module not available in Learnify."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        cache_key = (clean_course_code, last_mod)

        def load_docs():
            raw_docs = base_evaluator.vector_store.load_documents([clean_course_code])
            if not raw_docs:
                raise ValueError(f"No documents found for course_key '{clean_course_code}'.")
            for i, doc in enumerate(raw_docs):
                doc.metadata["chunk_index"] = i + 1
            return raw_docs

        def build_metadata(docs):
            return base_evaluator.extract_metadata(docs)

        try:
            metadata_json = acquire_metadata(cache_key, load_docs, build_metadata)
            return Response(metadata_json, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in ModuleMetadataView: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
