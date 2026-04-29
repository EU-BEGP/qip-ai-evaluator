# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import os
import json
import tempfile
import re

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, NotFound, APIException

from apps.evaluations.models import Evaluation, UserModule
from apps.evaluations.services.life_cycle_service import LifecycleService
from apps.evaluations.report_utils import ReportManager

logger = logging.getLogger(__name__)


class ReportService:
    """Service class responsible for generating reports for evaluations."""

    @staticmethod
    def generate_evaluation_pdf(evaluation_id, user):
        """Generates a PDF report for a given evaluation, ensuring the user has access and metadata is present."""

        evaluation = get_object_or_404(Evaluation.objects.select_related('module'), pk=evaluation_id)
        has_access = (evaluation.triggered_by == user) or UserModule.objects.filter(
            user=user, module=evaluation.module
        ).exists()

        if not has_access:
            raise PermissionDenied("Access denied.")

        if not evaluation.result_json:
            raise NotFound("Evaluation incomplete. Cannot generate PDF.")

        if not evaluation.metadata_json:
            LifecycleService.fetch_and_update_metadata(evaluation)
            evaluation.refresh_from_db()

        tmp_json_path, tmp_meta_path, tmp_pdf_path = "", "", ""

        try:
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp_json:
                json.dump(evaluation.result_json, tmp_json)
                tmp_json_path = tmp_json.name

            with tempfile.NamedTemporaryFile(mode='w+', suffix='_meta.json', delete=False) as tmp_meta:
                json.dump(evaluation.metadata_json or {}, tmp_meta)
                tmp_meta_path = tmp_meta.name

            tmp_pdf_path = f"{tmp_json_path}.pdf"
            ReportManager(tmp_json_path, tmp_meta_path).generate_pdf_report(tmp_pdf_path)

            if not os.path.exists(tmp_pdf_path):
                raise APIException("PDF generation failed.")

            with open(tmp_pdf_path, 'rb') as f:
                pdf_data = f.read()

            raw_title = evaluation.title or evaluation.module.title or "Untitled_Module"
            safe_title = re.sub(r'[\\/*?:"<>|]', "", raw_title).replace(" ", "_")
            filename = f"AI_Report_{safe_title}.pdf"

            return pdf_data, filename

        finally:
            for path in [tmp_json_path, tmp_meta_path, tmp_pdf_path]:
                if path and os.path.exists(path):
                    os.remove(path)
