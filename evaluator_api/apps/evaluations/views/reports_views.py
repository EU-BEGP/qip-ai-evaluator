# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from apps.evaluations.services.report_service import ReportService

logger = logging.getLogger(__name__)


@extend_schema(
    responses={(200, 'application/pdf'): OpenApiTypes.BINARY},
    description="Download evaluation report as PDF",
    tags=["reports"]
)
class ReportDownloadView(APIView):
    """API endpoint to handle PDF report generation and download for a specific evaluation."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        logger.info(f"PDF report requested for evaluation ID {pk} by user ID {request.user.id}")
        pdf_data, filename = ReportService.generate_evaluation_pdf(pk, request.user)
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        logger.info(f"PDF report served: '{filename}' for evaluation ID {pk}")
        return response
