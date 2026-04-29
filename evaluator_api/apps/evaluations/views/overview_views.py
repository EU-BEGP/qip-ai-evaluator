# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import F
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from apps.evaluations.models import Module, Evaluation, UserModule
from apps.evaluations.serializers.overview_serializers import (
    DashboardModuleSerializer, EvaluationHistorySerializer,
    ScanOverviewSerializer, LinkModuleSerializer, BasicInfoSerializer
)
from apps.evaluations.services.rag_service import RagService
from apps.evaluations.services.overview_service import DashboardService
from apps.evaluations.services.life_cycle_service import LifecycleService
from apps.evaluations.utils import extract_learnify_code

logger = logging.getLogger(__name__)


@extend_schema(tags=["overview"])
class DashboardListView(generics.ListAPIView):
    """API endpoint to retrieve the list of modules followed by the authenticated user."""

    permission_classes = [IsAuthenticated]
    serializer_class = DashboardModuleSerializer

    def get_queryset(self):
        return (
            Module.objects
            .filter(followed_by__user=self.request.user)
            .filter(evaluations__isnull=False)
            .distinct()
            .order_by("-followed_by__last_accessed")
        )

    def get_latest_evaluations(self, queryset):
        evaluations = (
            Evaluation.objects
            .filter(module__in=queryset)
            .select_related("module")
            .prefetch_related("scans")
            .order_by("module_id", F("evaluated_at").desc(nulls_last=True), "-created_at")
            .distinct("module_id")
        )
        return {e.module_id: e for e in evaluations}

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        latest_eval_map = self.get_latest_evaluations(queryset)
        course_keys = [m.course_key for m in queryset]
        rag_map = RagService.get_bulk_last_modified(course_keys)

        context = self.get_serializer_context()
        context.update({
            "latest_eval_map": latest_eval_map,
            "rag_map": rag_map
        })

        serializer = self.get_serializer(queryset, many=True, context=context)
        return Response(serializer.data)


@extend_schema(tags=["overview"])
class EvaluationHistoryListView(generics.GenericAPIView):
    """API endpoint to list the evaluation history for a given course key."""

    permission_classes = [IsAuthenticated]
    serializer_class = EvaluationHistorySerializer

    def post(self, request, *args, **kwargs):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        clean_link = input_serializer.validated_data['course_link'].split('?')[0]
        clean_key = extract_learnify_code(clean_link)
        queryset = (
            Evaluation.objects
            .filter(module__course_key=clean_key)
            .select_related('triggered_by')
            .order_by(F('evaluated_at').desc(nulls_last=True), '-created_at')[:20]
        )
        output_serializer = self.get_serializer(queryset, many=True)
        return Response(output_serializer.data)


@extend_schema(tags=["overview"])
class EvaluationStatusByIdView(generics.GenericAPIView):
    """API endpoint to retrieve the status of an evaluation by its ID."""

    permission_classes = [IsAuthenticated]
    serializer_class = ScanOverviewSerializer

    @extend_schema(operation_id="get_evaluation_status_by_id")
    def get(self, request, pk, *args, **kwargs):
        evaluation = get_object_or_404(
            Evaluation.objects.select_related('module', 'rubric').prefetch_related('scans'),
            pk=pk
        )
        data = DashboardService.build_overview(evaluation)
        serializer = self.get_serializer(data, many=True)
        return Response(serializer.data)


@extend_schema(tags=["overview"])
class LinkModuleView(generics.GenericAPIView):
    """Endpoint to retrieve module link by course_key."""

    permission_classes = [IsAuthenticated]
    serializer_class = LinkModuleSerializer

    def get(self, request, pk, *args, **kwargs):
        evaluation = get_object_or_404(Evaluation.objects.select_related('module'), pk=pk)
        has_access = (evaluation.triggered_by == request.user) or UserModule.objects.filter(
            user=request.user, module=evaluation.module
        ).exists()
        if not has_access:
            return Response(
                {"error": "Access denied. You do not have permission to view this module."},
                status=status.HTTP_403_FORBIDDEN
            )
        data = {"course_link": evaluation.module.course_link}
        serializer = self.get_serializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["overview"])
class EvaluationBasicInfoView(generics.RetrieveAPIView):
    """Endpoint to retrieve basic information about an evaluation, ensuring metadata is present."""

    permission_classes = [IsAuthenticated]
    serializer_class = BasicInfoSerializer
    queryset = Evaluation.objects.select_related('module')

    def get_object(self):
        evaluation = super().get_object()
        self._ensure_metadata(evaluation)
        return evaluation

    def _ensure_metadata(self, evaluation):
        if LifecycleService.is_metadata_valid(evaluation):
            return

        logger.info(f"Metadata missing (Eval {evaluation.id}). Queueing async fetch.")

        try:
            from apps.evaluations.tasks import async_sync_module_metadata
            async_sync_module_metadata.delay(evaluation.id)
        except Exception as e:
            logger.error(f"Failed to queue metadata fetch for Eval {evaluation.id}: {e}")
