# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import datetime
from dateutil.tz import gettz

from apps.evaluations.services.rag_service import RagService

_AMSTERDAM_TZ = gettz("Europe/Amsterdam")
logger = logging.getLogger(__name__)


class DashboardService:
    """Business logic for dashboard metrics and status determination."""

    @staticmethod
    def _determine_status(latest_eval, rag_date):
        if not latest_eval:
            return "Not Started"
        if RagService.is_outdated(rag_date, latest_eval.evaluated_at):
            return "Outdated"
        return "Updated"

    @staticmethod
    def _calculate_global_avg(ai, peer):
        scores = [s for s in [ai, peer] if s is not None]
        return round(sum(scores) / len(scores), 2) if scores else None

    @staticmethod
    def _rag_date_to_utc_display(rag_date) -> str | None:
        if not rag_date:
            return None
        naive = rag_date.replace(tzinfo=None)
        amsterdam_dt = naive.replace(tzinfo=_AMSTERDAM_TZ)
        utc_dt = amsterdam_dt.astimezone(datetime.timezone.utc)
        return utc_dt.strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def build_overview(evaluation):
        rag_date = RagService.get_last_modified(evaluation.module.course_key)

        is_outdated = (
            RagService.is_outdated(rag_date, evaluation.evaluated_at)
            if evaluation.evaluated_at
            else False
        )

        existing_scans = {s.scan_type: s for s in evaluation.scans.all()}
        overview = []
        missing_scans = 0

        for s_type, scan in existing_scans.items():
            scan_data = {
                "name": s_type,
                "id": scan.id if scan else None,
                "status": scan.get_status_display() if scan else "Not Started",
                "evaluable": bool(scan) and scan.status not in ['IN_PROGRESS', 'COMPLETED'] and not is_outdated,
                "scan_average": scan.scan_average if scan else None,
                "scan_max": 5.0,
                "outdated": is_outdated,
            }
            if not scan:
                missing_scans += 1
            overview.append(scan_data)

        overview.insert(0, {
            "name": "All Scans",
            "id": evaluation.id,
            "evaluable": missing_scans > 0 and not is_outdated,
            "scan_average": evaluation.ai_average,
            "scan_max": 5.0,
            "status": evaluation.get_status_display(),
            "outdated": is_outdated,
        })

        return overview
