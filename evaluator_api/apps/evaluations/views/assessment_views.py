# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.evaluations.security import accessible_evaluations, accessible_scans
from apps.evaluations.serializers.assessment_serializers import ResultSerializer

logger = logging.getLogger(__name__)


@extend_schema(tags=["AI / RAG"])
class ResultDetailView(generics.GenericAPIView):
    """Returns the result_json for an Evaluation or Scan the user may access."""

    permission_classes = [IsAuthenticated]
    serializer_class = ResultSerializer

    def get(self, request, pk, model_type):
        queryset_map = {
            'module': accessible_evaluations,
            'scan': accessible_scans,
        }
        get_accessible = queryset_map.get(model_type)
        if not get_accessible:
            return Response({"detail": "Invalid model_type"}, status=status.HTTP_400_BAD_REQUEST)
        instance = get_object_or_404(get_accessible(request.user), pk=pk)
        return Response(instance.result_json or {}, status=status.HTTP_200_OK)
