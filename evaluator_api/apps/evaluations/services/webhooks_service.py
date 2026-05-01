# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from apps.evaluations.models import Evaluation, Scan
from apps.evaluations.services.rag_service import RagService

logger = logging.getLogger(__name__)


class WebhookHandlerService:
    """Processes and routes all asynchronous webhook events from the RAG system."""

    _HANDLERS = {
        "SNAPSHOT_CREATED": lambda e, d: WebhookHandlerService._handle_snapshot(e, d),
        "CRITERION_COMPLETE": lambda e, d: WebhookHandlerService._handle_interim_progress(e, d),
        "COMPLETE": lambda e, d: WebhookHandlerService._handle_completion(e, d),
        "FAILED": lambda e, d: WebhookHandlerService._handle_failure(e, d),
    }

    @staticmethod
    def process_callback(evaluation, data):
        """Acts as a traffic router for different webhook statuses."""

        status_cb = data.get("status")
        logger.debug(f"Routing webhook status '{status_cb}' for Evaluation ID {evaluation.id}")

        if evaluation.status == Evaluation.Status.COMPLETED:
            return "Already finished"

        handler = WebhookHandlerService._HANDLERS.get(status_cb)

        if not handler:
            raise ValueError(f"Unknown webhook status: {status_cb}")

        return handler(evaluation, data)

    @staticmethod
    def _handle_snapshot(evaluation, data):
        """Saves the document context snapshot. First write wins — never overwrites an existing snapshot."""

        from django.core.cache import cache

        result = data.get('result')
        if result and isinstance(result, str) and not evaluation.document_snapshot:
            updated = (
                Evaluation.objects
                .filter(id=evaluation.id, document_snapshot="")
                .update(document_snapshot=result)
            )
            if updated:
                evaluation.document_snapshot = result
                cache.delete(f"snapshot:lock:{evaluation.id}")
        return "Snapshot saved"

    @staticmethod
    def _handle_interim_progress(evaluation, data):
        """Marks a single scan COMPLETED when its result arrives, then checks overall status."""

        import time
        from django.core.cache import cache
        from apps.evaluations.tasks import WATCHDOG_CACHE_KEY

        result = data.get('result')
        if not result or 'content' not in result:
            raise ValueError("Invalid payload for CRITERION_COMPLETE")

        scan_data = result['content'][0]
        s_name = scan_data.get('scan')
        valid_types = evaluation.rubric.available_scans if evaluation.rubric else []

        if s_name in valid_types:
            Scan.objects.update_or_create(
                evaluation=evaluation,
                scan_type=s_name,
                defaults={'status': Scan.Status.IN_PROGRESS, 'result_json': result}
            )
            WebhookHandlerService._merge_scan_results(evaluation, [scan_data])
        cache.set(WATCHDOG_CACHE_KEY.format(evaluation.id), time.time(), timeout=7200)

        return "Interim progress saved"

    @staticmethod
    def _handle_completion(evaluation, data):
        """Finalizes the evaluation, triggers notifications, and updates master states."""

        from apps.notifications.models import Message
        result_payload = data.get('result')
        if not result_payload:
            raise ValueError("Invalid payload for COMPLETE")

        if result_payload.get('title'):
            clean_title = RagService.clean_title(result_payload['title'])
            evaluation.title = clean_title
            if evaluation.module:
                evaluation.module.title = clean_title
                evaluation.module.save(update_fields=['title'])

        valid_types = evaluation.rubric.available_scans if evaluation.rubric else []
        new_content = result_payload.get('content', [])

        for scan_data in new_content:
            s_name = scan_data.get('scan')
            if s_name in valid_types:
                Scan.objects.update_or_create(
                    evaluation=evaluation,
                    scan_type=s_name,
                    defaults={
                        'status': Scan.Status.COMPLETED,
                        'result_json': {"title": evaluation.title, "content": [scan_data]}
                    }
                )

                if evaluation.triggered_by:
                    title_text = evaluation.title or evaluation.module.title or "Module"
                    Message.objects.get_or_create(
                        user=evaluation.triggered_by,
                        evaluation=evaluation,
                        scan_type=s_name,
                        defaults={
                            "title": f"{s_name} Finished: {title_text}",
                            "content": f"The {s_name} has finished successfully.",
                            "is_read": False
                        }
                    )

        WebhookHandlerService._merge_scan_results(evaluation, new_content, save=False)
        WebhookHandlerService._check_and_update_status(evaluation)
        return "Completed processed"

    @staticmethod
    def _handle_failure(evaluation, data):
        """Cleans up failed scans and registers error states."""

        failed_scans = data.get('scan_names', [])

        if failed_scans:
            Scan.objects.filter(evaluation=evaluation, scan_type__in=failed_scans).update(status=Scan.Status.FAILED)
        else:
            Scan.objects.filter(evaluation=evaluation, status=Scan.Status.IN_PROGRESS).update(status=Scan.Status.FAILED)

        if evaluation.result_json and 'content' in evaluation.result_json:
            current_content = evaluation.result_json.get('content', [])
            clean_content = [item for item in current_content if item.get('scan') not in failed_scans]
            evaluation.result_json['content'] = clean_content

        evaluation.error_message = data.get('error', "Unknown error")
        evaluation.save(update_fields=['error_message', 'result_json'])
        WebhookHandlerService._check_and_update_status(evaluation)

        return "Failure processed (Partial)"

    @staticmethod
    def _merge_scan_results(evaluation, new_content_list, save=True):
        """Centralizes logic to merge new scan results into the evaluation JSON."""

        current_json = evaluation.result_json or {"title": evaluation.title, "content": []}
        current_content = current_json.get("content", [])

        content_map = {item.get('scan'): item for item in current_content}

        for new_item in new_content_list:
            scan_type = new_item.get('scan')
            if scan_type:
                content_map[scan_type] = new_item

        evaluation.result_json = {
            "title": evaluation.title or current_json.get('title'),
            "content": list(content_map.values())
        }

        if save:
            evaluation.save(update_fields=['result_json'])

    @staticmethod
    def _check_and_update_status(evaluation):
        """Verifies if all required scans have finished and updates Evaluation status."""

        completed_types = set(
            Scan.objects.filter(
                evaluation=evaluation,
                status=Scan.Status.COMPLETED
            ).values_list("scan_type", flat=True)
        )
        all_possible_types = set(evaluation.rubric.available_scans if evaluation.rubric else [])

        if all_possible_types and all_possible_types.issubset(completed_types):
            evaluation.status = Evaluation.Status.COMPLETED
        else:
            evaluation.status = Evaluation.Status.INCOMPLETED

        evaluation.save(update_fields=['status'])
