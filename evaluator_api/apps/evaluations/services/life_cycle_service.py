# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.urls import reverse

from apps.evaluations.models import Module, UserModule, Evaluation, Scan, Rubric
from apps.evaluations.services.rag_service import RagService
from apps.evaluations.utils import extract_learnify_code

logger = logging.getLogger(__name__)


class LifecycleService:
    """Manages the creation and state of module evaluations."""

    @staticmethod
    def ensure_module_access(user, course_link):
        """Links the module to the user's dashboard."""

        clean_link = course_link.split('?')[0]
        short_key = extract_learnify_code(clean_link)
        if not short_key:
            raise ValueError(f"Could not extract module key from: {course_link}")
        module, _ = Module.objects.get_or_create(course_key=short_key)
        if not module.course_link:
            module.course_link = clean_link
            module.save(update_fields=['course_link'])
        UserModule.objects.update_or_create(user=user, module=module)
        logger.info(f"Verified module access for user ID {user.id} to module ID {module.id}")
        return module

    @staticmethod
    @transaction.atomic
    def get_or_create_evaluation_structure(module, user):
        """Builds the core evaluation structure."""

        logger.info(f"Initiating evaluation structure check for module ID {module.id} by user ID {user.id}")
        locked_module = Module.objects.select_for_update().get(id=module.id)

        active_rubric = Rubric.objects.first()
        if not active_rubric:
            logger.critical("System misconfiguration: No active rubric found in database")
            raise ValueError("No active rubric found.")

        latest_eval = (
            Evaluation.objects
            .filter(module=locked_module)
            .only("status", "evaluated_at", "id")
            .order_by("-created_at")
            .first()
        )

        if not LifecycleService._requires_new_evaluation(locked_module, latest_eval):
            logger.info(f"Reusing existing evaluation ID {latest_eval.id} for module ID {locked_module.id}")
            return latest_eval, False

        evaluation = Evaluation.objects.create(
            module=locked_module,
            triggered_by=user,
            rubric=active_rubric,
            status=Evaluation.Status.NOT_STARTED,
            title=locked_module.title or "New Evaluation",
        )
        logger.info(f"Created new evaluation ID {evaluation.id} for module ID {locked_module.id}")

        LifecycleService._build_scans(evaluation, active_rubric)
        LifecycleService._sync_module_metadata(evaluation)

        return evaluation, True

    @staticmethod
    def _requires_new_evaluation(module, latest_eval):
        if not latest_eval:
            return True

        if latest_eval.status == Evaluation.Status.NOT_STARTED:
            return False

        rag_date = RagService.get_last_modified(module.course_key, force=True)
        return RagService.is_outdated(rag_date, latest_eval.evaluated_at)

    _METADATA_PLACEHOLDERS = frozenset({
        "N/A", "No abstract available.", "New Evaluation",
        "No teachers information available.",
    })
    _METADATA_STRING_FIELDS = (
        "elh", "eqf", "smcts", "abstract", "title",
        "suggested_knowledge", "suggested_skills", "suggested_ra",
    )
    _METADATA_LIST_FIELDS = ("keywords", "teachers")

    @staticmethod
    def is_metadata_valid(evaluation) -> bool:
        meta = evaluation.metadata_json
        if not meta:
            return False
        if evaluation.title in LifecycleService._METADATA_PLACEHOLDERS:
            return False
        for field in LifecycleService._METADATA_STRING_FIELDS:
            if meta.get(field) in LifecycleService._METADATA_PLACEHOLDERS:
                return False
        for field in LifecycleService._METADATA_LIST_FIELDS:
            val = meta.get(field)
            if isinstance(val, list) and not val:
                return False
        return True

    @staticmethod
    def fetch_and_update_metadata(evaluation):
        """Fetches remote metadata for an evaluation and updates it in the database."""

        if LifecycleService.is_metadata_valid(evaluation):
            return

        logger.info(f"Fetching remote metadata for evaluation ID {evaluation.id}")
        metadata = RagService.fetch_metadata(evaluation.module.course_key)

        if metadata:
            evaluation.metadata_json = metadata
            evaluation.save(update_fields=['metadata_json'])
            logger.info(f"Successfully updated metadata for evaluation ID {evaluation.id}")
        else:
            logger.warning(f"Failed to fetch or received empty metadata for evaluation ID {evaluation.id}")

    @staticmethod
    def _sync_module_metadata(evaluation):
        """Queues metadata retrieval without blocking the main transaction."""

        from apps.evaluations.tasks import async_sync_module_metadata
        transaction.on_commit(lambda: async_sync_module_metadata.delay(evaluation.id))
        logger.info(f"Metadata sync queued to Celery for evaluation ID {evaluation.id}")

    @staticmethod
    def _build_scans(evaluation, active_rubric):
        """Initializes Scan objects based on the rubric's available scans."""

        logger.info(f"Building scan structure for evaluation ID {evaluation.id}")
        valid_scans = active_rubric.available_scans
        if not valid_scans:
            logger.error(
                f"No valid scans found in active rubric ID {active_rubric.id} for evaluation ID {evaluation.id}"
            )
            return

        Scan.objects.bulk_create([
            Scan(evaluation=evaluation, scan_type=st, status=Scan.Status.PENDING)
            for st in valid_scans
        ])
        logger.info(f"Successfully built {len(valid_scans)} scans for evaluation ID {evaluation.id}")

    @staticmethod
    def _get_target_scans_and_id(evaluation, scan_name):
        """Determines the exact scans to target and validates they exist in the rubric."""

        is_all_scans = not scan_name or scan_name.lower() == 'all scans'
        valid_scans = evaluation.rubric.available_scans if evaluation.rubric else []

        if is_all_scans:
            target_scans = valid_scans
            final_scan_id = str(evaluation.id)
        else:
            if scan_name not in valid_scans:
                raise ValueError(f"Invalid scan type '{scan_name}'. Must be one of: {valid_scans}")

            target_scans = [scan_name]
            scan_obj = Scan.objects.get(evaluation=evaluation, scan_type=scan_name)
            final_scan_id = str(scan_obj.id)

        return target_scans, final_scan_id, is_all_scans

    @staticmethod
    def _prepare_database_states(evaluation, target_scans, is_all_scans):
        """Filters out completed scans and updates the database statuses to IN_PROGRESS."""

        with transaction.atomic():
            locked_eval = Evaluation.objects.select_for_update().get(id=evaluation.id)
            non_runnable_scans = set(Scan.objects.filter(
                evaluation=locked_eval,
                scan_type__in=target_scans,
                status__in=[Scan.Status.COMPLETED, Scan.Status.IN_PROGRESS]
            ).values_list('scan_type', flat=True))

            scans_to_run = [s for s in target_scans if s not in non_runnable_scans]

            if scans_to_run:
                logger.debug(f"Updating database status for scans: {scans_to_run} in evaluation ID {locked_eval.id}")
                Scan.objects.filter(
                    evaluation=locked_eval, scan_type__in=scans_to_run
                ).update(status=Scan.Status.IN_PROGRESS)
                locked_eval.requested_scans = list(set((locked_eval.requested_scans or []) + scans_to_run))

                locked_eval.status = (
                    Evaluation.Status.IN_PROGRESS
                    if is_all_scans
                    else Evaluation.Status.INCOMPLETED
                )

                locked_eval.save(update_fields=["requested_scans", "status"])
                evaluation.requested_scans = locked_eval.requested_scans
                evaluation.status = locked_eval.status

        return scans_to_run

    @staticmethod
    def _try_reuse_existing_results(evaluation):
        """Attempts to reuse results from an existing up-to-date evaluation. Returns True if reused."""

        if evaluation.status != Evaluation.Status.NOT_STARTED:
            return False

        candidate = (
            Evaluation.objects
            .filter(module=evaluation.module)
            .exclude(id=evaluation.id)
            .exclude(status__in=[Evaluation.Status.NOT_STARTED, Evaluation.Status.IN_PROGRESS])
            .order_by("-created_at")
            .first()
        )

        if not candidate:
            return False

        rag_modified = RagService.get_last_modified(evaluation.module.course_key, force=True)

        if RagService.is_outdated(rag_modified, candidate.evaluated_at):
            return False

        logger.info(f"Reusing evaluation results from evaluation {candidate.id} for evaluation {evaluation.id}")

        evaluation.document_snapshot = candidate.document_snapshot
        evaluation.status = candidate.status
        evaluation.evaluated_at = candidate.evaluated_at
        evaluation.result_json = candidate.result_json
        evaluation.save(update_fields=["document_snapshot", "status", "evaluated_at", "result_json"])

        candidate_scans = {
            s.scan_type: s
            for s in Scan.objects.filter(evaluation=candidate).only("scan_type", "result_json", "status")
        }

        to_update = []
        for scan in Scan.objects.filter(evaluation=evaluation):
            old = candidate_scans.get(scan.scan_type)
            if old:
                scan.result_json = old.result_json
                scan.status = old.status
                to_update.append(scan)

        Scan.objects.bulk_update(to_update, ["result_json", "status"])

        return True

    @staticmethod
    def start_evaluation_process(evaluation, scan_name, user):
        """Orchestrates scan preparation, database updates, and queues the RAG webhook task."""

        from apps.evaluations.tasks import (async_trigger_rag_evaluation, async_check_evaluation_timeout)

        logger.info(f"Starting evaluation process for evaluation ID {evaluation.id} triggered by user ID {user.id}")
        target_scans, final_scan_id, is_all_scans = LifecycleService._get_target_scans_and_id(evaluation, scan_name)

        if evaluation.status == Evaluation.Status.COMPLETED:
            logger.info(f"Evaluation ID {evaluation.id} already completed. Skipping restart.")
            return {
                "message": "Evaluation already completed.",
                "evaluation_id": str(evaluation.id),
                "scan_id": final_scan_id
            }

        reused = LifecycleService._try_reuse_existing_results(evaluation)
        if reused:
            logger.info(f"Reusing previous evaluation for {evaluation.id}")

        if not evaluation.evaluated_at:
            rag_modified = RagService.get_last_modified(evaluation.module.course_key, force=True)
            if not rag_modified:
                rag_modified = timezone.now()
            evaluation.evaluated_at = rag_modified
            evaluation.save(update_fields=['evaluated_at'])

        scans_to_run = LifecycleService._prepare_database_states(evaluation, target_scans, is_all_scans)

        if not scans_to_run:
            logger.info(f"All requested scans are already completed for evaluation ID {evaluation.id}")
            return {
                "message": "All requested scans are already completed.",
                "evaluation_id": str(evaluation.id),
                "scan_id": final_scan_id
            }

        # Refresh snapshot
        evaluation.refresh_from_db(fields=["document_snapshot"])

        base_url = settings.PUBLIC_BASE_URL.rstrip("/")
        payload = {
            "evaluation_id": evaluation.id,
            "course_key": evaluation.module.course_key,
            "callback_url": f"{base_url}{reverse('evaluation_callback')}",
            "qip_user_id": str(user.id),
            "scan_names": scans_to_run,
            "existing_snapshot": evaluation.document_snapshot or None,
        }

        from django.core.cache import cache
        import time
        from apps.evaluations.tasks import WATCHDOG_INACTIVITY_TIMEOUT, WATCHDOG_CACHE_KEY

        async_trigger_rag_evaluation.delay(evaluation.id, scans_to_run, payload)
        logger.info(f"RAG trigger task queued to Celery for evaluation ID {evaluation.id}")

        cache.set(WATCHDOG_CACHE_KEY.format(evaluation.id), time.time(), timeout=7200)
        async_check_evaluation_timeout.apply_async(args=[evaluation.id, scans_to_run], countdown=WATCHDOG_INACTIVITY_TIMEOUT)
        logger.info(f"Watchdog armed for Evaluation {evaluation.id} (inactivity timeout={WATCHDOG_INACTIVITY_TIMEOUT}s).")

        return {
            "message": "Evaluation started.",
            "evaluation_id": str(evaluation.id),
            "scan_id": final_scan_id
        }
