# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.evaluations.models import Evaluation, Scan
from apps.evaluations.serializers.assessment_serializers import ResultSerializer

logger = logging.getLogger(__name__)


@extend_schema(tags=["AI / RAG"])
class ResultDetailView(generics.GenericAPIView):
    """Returns the result_json for an Evaluation or Scan."""

    permission_classes = [IsAuthenticated]
    serializer_class = ResultSerializer
    model_map = {
        'module': Evaluation,
        'scan': Scan,
    }

    def get(self, request, pk, model_type):
        model_class = self.model_map.get(model_type)
        if not model_class:
            return Response({"detail": "Invalid model_type"}, status=status.HTTP_400_BAD_REQUEST)
        instance = get_object_or_404(model_class, pk=pk)
        return Response(instance.result_json or {}, status=status.HTTP_200_OK)
