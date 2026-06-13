# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.urls import reverse

from apps.evaluations.models import Module, UserModule, Evaluation, Scan, Rubric
from apps.evaluations.services import watchdog_service as watchdog
from apps.evaluations.services.rag_service import RagService
from apps.evaluations.utils import extract_learnify_code

logger = logging.getLogger(__name__)


class ContentServiceUnavailableError(Exception):
    """Raised when the content service (Learnify) is unreachable."""


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
            rag_date = RagService.get_last_modified(module.course_key, force=True)
            if not rag_date:
                raise ContentServiceUnavailableError(
                    "The content service is temporarily unavailable. Please try again later."
                )
            return True

        if latest_eval.status == Evaluation.Status.NOT_STARTED:
            return False

        rag_date = RagService.get_last_modified(module.course_key, force=True)
        return RagService.is_outdated(rag_date, latest_eval.evaluated_at)

    @staticmethod
    def fetch_and_update_metadata(evaluation):
        """Fetches remote metadata for an evaluation and updates it. First write wins."""

        if evaluation.metadata_json:
            return

        logger.info(f"Fetching remote metadata for evaluation ID {evaluation.id}")
        metadata = RagService.fetch_metadata(evaluation.module.course_key)

        if metadata:
            updated = (
                Evaluation.objects
                .filter(id=evaluation.id, metadata_json={})
                .update(metadata_json=metadata)
            )
            if updated:
                evaluation.metadata_json = metadata
                logger.info(f"Successfully updated metadata for evaluation ID {evaluation.id}")
            else:
                logger.debug(f"Metadata already set by another writer for evaluation ID {evaluation.id}")
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
    def start_evaluation_process(evaluation, scan_name, user):
        """Orchestrates scan preparation, database updates, and queues the RAG webhook task."""

        from apps.evaluations.tasks import async_trigger_rag_evaluation

        logger.info(f"Starting evaluation process for evaluation ID {evaluation.id} triggered by user ID {user.id}")
        target_scans, final_scan_id, is_all_scans = LifecycleService._get_target_scans_and_id(evaluation, scan_name)

        if evaluation.status == Evaluation.Status.COMPLETED:
            logger.info(f"Evaluation ID {evaluation.id} already completed. Skipping restart.")
            return {
                "message": "Evaluation already completed.",
                "evaluation_id": str(evaluation.id),
                "scan_id": final_scan_id
            }

        if not evaluation.evaluated_at:
            rag_modified = RagService.get_last_modified(evaluation.module.course_key, force=True)
            if not rag_modified:
                raise ContentServiceUnavailableError(
                    "The content service is temporarily unavailable. Please try again later."
                )
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

        # Watchdog is armed 
        async_trigger_rag_evaluation.delay(evaluation.id, scans_to_run, payload)
        logger.info(f"RAG trigger task queued to Celery for evaluation ID {evaluation.id}")

        return {
            "message": "Evaluation started.",
            "evaluation_id": str(evaluation.id),
            "scan_id": final_scan_id
        }

    @staticmethod
    def recompute_evaluation_status(evaluation):
        """Derives the Evaluation status from its current Scan states."""

        scan_statuses = set(
            Scan.objects.filter(evaluation=evaluation).values_list("status", flat=True)
        )

        if not scan_statuses:
            evaluation.status = Evaluation.Status.NOT_STARTED
        elif scan_statuses == {Scan.Status.COMPLETED}:
            evaluation.status = Evaluation.Status.COMPLETED
        elif scan_statuses == {Scan.Status.FAILED}:
            evaluation.status = Evaluation.Status.FAILED
        elif Scan.Status.IN_PROGRESS in scan_statuses:
            evaluation.status = Evaluation.Status.IN_PROGRESS
        else:
            evaluation.status = Evaluation.Status.INCOMPLETED

        evaluation.save(update_fields=["status"])
        logger.debug(f"Evaluation {evaluation.id} status recomputed to {evaluation.status}")

    @staticmethod
    def mark_failed(evaluation, scan_types, reason, run_id=None):
        """Marks the given scans as FAILED and cleans up locks, watchdogs, and remote runs."""

        if not scan_types:
            scan_types = list(
                Scan.objects
                .filter(evaluation=evaluation, status=Scan.Status.IN_PROGRESS)
                .values_list("scan_type", flat=True)
            )

        if scan_types:
            Scan.objects.filter(
                evaluation=evaluation, scan_type__in=scan_types
            ).update(status=Scan.Status.FAILED)
            logger.warning(
                f"Marked scans {scan_types} as FAILED for evaluation {evaluation.id}: {reason}"
            )

            if evaluation.triggered_by:
                from apps.notifications.models import Message
                module_title = evaluation.module.title if evaluation.module else None
                title_text = evaluation.title or module_title or "Module"
                for s_name in scan_types:
                    Message.objects.get_or_create(
                        user=evaluation.triggered_by,
                        evaluation=evaluation,
                        scan_type=s_name,
                        level=Message.Level.ERROR,
                        defaults={
                            "title": f"{s_name} Failed: {title_text}",
                            "content": f"The {s_name} could not be evaluated. You can try running it again.",
                            "is_read": False,
                        },
                    )

        if evaluation.result_json and 'content' in evaluation.result_json:
            current_content = evaluation.result_json.get('content', [])
            clean_content = [item for item in current_content if item.get('scan') not in scan_types]
            evaluation.result_json['content'] = clean_content

        evaluation.error_message = reason
        evaluation.save(update_fields=['error_message', 'result_json'])

        LifecycleService.recompute_evaluation_status(evaluation)

        watchdog.disarm(evaluation.id, scan_types)
        cache.delete(f"snapshot:lock:{evaluation.id}")

        if run_id:
            from apps.evaluations.tasks.evaluation import async_cancel_rag_evaluation
            async_cancel_rag_evaluation.delay(run_id)
