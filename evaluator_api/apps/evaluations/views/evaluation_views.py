# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema

from apps.evaluations.models import Evaluation
from apps.evaluations.services.life_cycle_service import LifecycleService, ContentServiceUnavailableError
from apps.evaluations.services.webhooks_service import WebhookHandlerService
from apps.evaluations.security import verify_rag_callback, accessible_evaluations, accessible_scans
from apps.evaluations.serializers.evaluation_serializers import (
    EvaluationStatusSerializer,
    ScanStatusSerializer,
    StartEvaluationSerializer,
    WebhookCallbackSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(tags=["lifecycle"])
class EvaluationStatusView(generics.RetrieveAPIView):
    """Retrieves the current status of an Evaluation the user may access."""

    permission_classes = [IsAuthenticated]
    serializer_class = EvaluationStatusSerializer

    def get_queryset(self):
        return accessible_evaluations(self.request.user).select_related('module')


@extend_schema(tags=["lifecycle"])
class ScanStatusView(generics.RetrieveAPIView):
    """Retrieves the current status of a specific Scan the user may access."""

    permission_classes = [IsAuthenticated]
    serializer_class = ScanStatusSerializer

    def get_queryset(self):
        return accessible_scans(self.request.user).select_related('evaluation__module')


@extend_schema(tags=["AI / RAG"])
class StartEvaluationView(generics.GenericAPIView):
    """Gets or creates an evaluation for the given module, then triggers the RAG evaluation."""

    permission_classes = [IsAuthenticated]
    serializer_class = StartEvaluationSerializer

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        logger.info(f"Received evaluate request from user ID {user_id}")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        course_link = serializer.validated_data['course_link']
        scan_name = serializer.validated_data.get('scan_name')

        try:
            module = LifecycleService.ensure_module_access(request.user, course_link)
            evaluation, created = LifecycleService.get_or_create_evaluation_structure(module, request.user)
            logger.info(f"Evaluation {'created' if created else 'reused'}: ID {evaluation.id} for module {module.id}")
        except ContentServiceUnavailableError as e:
            logger.warning(f"Content service unavailable for user ID {user_id}: {str(e)}")
            return Response({"error": "Content service temporarily unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ValueError as e:
            logger.error(f"Failed to get/create evaluation for user ID {user_id}: {str(e)}")
            return Response({"error": "Invalid evaluation request."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = LifecycleService.start_evaluation_process(
                evaluation=evaluation, scan_name=scan_name, user=request.user
            )
            logger.info(f"Evaluation started for evaluation ID {evaluation.id}")
            return Response(result, status=status.HTTP_202_ACCEPTED)

        except ContentServiceUnavailableError as e:
            logger.warning(f"Content service unavailable for user ID {user_id}: {str(e)}")
            return Response({"error": "Content service temporarily unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ValueError as e:
            logger.error(f"Validation error starting evaluation for user ID {user_id}: {str(e)}")
            return Response({"error": "Invalid evaluation request."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error starting evaluation for user ID {user_id}: {str(e)}", exc_info=True)
            return Response({"error": "Internal server error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(tags=["webhooks"])
class EvaluationCallbackView(generics.GenericAPIView):
    """Handles asynchronous webhook callbacks from the RAG system."""

    permission_classes = [AllowAny]
    serializer_class = WebhookCallbackSerializer

    @method_decorator(verify_rag_callback)
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        logger.info("Received external RAG webhook callback")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evaluation = serializer.validated_data['evaluation']
        evaluation = Evaluation.objects.select_for_update().get(id=evaluation.id)
        message = WebhookHandlerService.process_callback(evaluation, serializer.validated_data)

        return Response({"message": message}, status=status.HTTP_200_OK)
