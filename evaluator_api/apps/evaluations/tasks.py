from celery import shared_task
from django.db import transaction
import logging
import requests
from django.conf import settings
from .models import Evaluation, Scan

logger = logging.getLogger(__name__)

def fetch_and_update_metadata(evaluation):
    if evaluation.metadata_json:
        return 

    try:
        url = getattr(settings, 'RAG_API_METADATA_URL', None)
        if url:
            response = requests.post(
                url,
                json={'course_key': evaluation.module.course_key},
                timeout=300
            )
            response.raise_for_status()
            evaluation.metadata_json = response.json()
            evaluation.save(update_fields=['metadata_json'])
    except Exception as e:
        logger.error(f"Failed to fetch metadata for evaluation {evaluation.id}: {e}")

@shared_task
def check_and_merge_evaluation(evaluation_id):
    try:
        with transaction.atomic():
            evaluation = Evaluation.objects.select_for_update().get(id=evaluation_id)

            if evaluation.status == Evaluation.Status.COMPLETED:
                return
            
            # Merge content
            all_relevant_scans = evaluation.scans.filter(
                status__in=[Scan.Status.COMPLETED, Scan.Status.IN_PROGRESS]
            ).exclude(result_json__isnull=True).order_by('scan_type')
            
            final_content_list = []
            final_title = evaluation.title or ""

            for scan in all_relevant_scans:
                if not final_title and scan.result_json and 'title' in scan.result_json:
                    final_title = scan.result_json['title']

                if (scan.result_json and 
                    'content' in scan.result_json and 
                    isinstance(scan.result_json['content'], list)):
                    final_content_list.extend(scan.result_json['content'])
            
            final_json = {
                "title": final_title,
                "content": final_content_list
            }
            evaluation.result_json = final_json
            
            completed_scan_types = set(
                s.scan_type for s in all_relevant_scans if s.status == Scan.Status.COMPLETED
            )
            all_possible_scans = set(Scan.ScanType.values)
            
            if all_possible_scans.issubset(completed_scan_types):
                evaluation.status = Evaluation.Status.COMPLETED
                fetch_and_update_metadata(evaluation)
            evaluation.save()

    except Evaluation.DoesNotExist:
        logger.error(f"Task Error: Evaluation {evaluation_id} not found.")
    except Exception as e:
        logger.error(f"Critical error merging evaluation {evaluation_id}: {e}", exc_info=True)
