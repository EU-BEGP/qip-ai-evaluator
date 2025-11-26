from celery import shared_task
from django.db import transaction
import logging
import requests
from django.conf import settings
from .models import Evaluation, Scan, Message

logger = logging.getLogger(__name__)

def fetch_and_update_metadata(evaluation):
    """
    Fetches metadata from the AI endpoint if it doesn't exist.
    """
    if evaluation.metadata_json:
        return 

    try:
        url = settings.RAG_API_METADATA_URL 
        response = requests.post(
            url,
            json={'course_key': evaluation.module.course_key},
            timeout=300
        )
        response.raise_for_status()
        
        evaluation.metadata_json = response.json()
        evaluation.save(update_fields=['metadata_json'])
        logger.info(f"Metadata saved for evaluation {evaluation.id}")
        
    except Exception as e:
        logger.error(f"Failed to fetch metadata for evaluation {evaluation.id}: {e}")

@shared_task
def check_and_merge_evaluation(evaluation_id):
    """
    Checks if a batch of requested scans is done.
    If so, it merges the JSON of *all* completed scans and updates the
    Evaluation's status (COMPLETED or IN_PROGRESS).
    """
    try:
        with transaction.atomic():
            evaluation = Evaluation.objects.select_for_update().get(id=evaluation_id)

            # If already fully COMPLETED (6/6 scans), do nothing.
            if evaluation.status == Evaluation.Status.COMPLETED:
                logger.info(f"Evaluation {evaluation_id} is already COMPLETED. Skipping.")
                return

            # --- 1. Check if the current batch failed ---
            # Get scans requested in this batch
            requested_scan_types = set(evaluation.requested_scans)
            
            # Get *all* failed scans for this evaluation
            failed_scans = evaluation.scans.filter(status=Scan.Status.FAILED)
            failed_scan_types = set(s.scan_type for s in failed_scans)

            # If *any* of the scans from *this batch* failed,
            # mark the Evaluation as FAILED and do not merge.
            if any(s_type in failed_scan_types for s_type in requested_scan_types):
                evaluation.status = Evaluation.Status.FAILED
                evaluation.error_message = "One or more scans failed in the last batch."
                evaluation.result_json = None # Clear old JSON
                evaluation.save()
                logger.warning(f"Evaluation {evaluation_id} marked as FAILED due to a failed scan.")
                return
            
            # --- 3. Merge JSON (Smart Merge: Completed + In Progress) ---
            
            all_relevant_scans = evaluation.scans.filter(
                status__in=[Scan.Status.COMPLETED, Scan.Status.IN_PROGRESS]
            ).exclude(result_json__isnull=True).order_by('scan_type')
            
            final_content_list = []
            final_title = evaluation.title or "" # Use existing title as fallback

            # Iteramos sobre todos los scans relevantes
            for scan in all_relevant_scans:
                # 3a. Get the real title from the first valid scan
                if not final_title and scan.result_json and 'title' in scan.result_json:
                    final_title = scan.result_json['title']

                # 3b. Merge the *inner* content from EACH scan
                if (scan.result_json and 
                    'content' in scan.result_json and 
                    isinstance(scan.result_json['content'], list)):
                    
                    # THE KEY LOGIC:
                    # Extend the main list with the *items* from the inner list
                    final_content_list.extend(scan.result_json['content'])
            
            # 3c. Build the final JSON
            final_json = {
                "title": final_title,
                "content": final_content_list
            }
            evaluation.result_json = final_json
            
            # --- 4. Set Final Status (COMPLETED or IN_PROGRESS) ---
            
            completed_scan_types = set(
                s.scan_type for s in all_relevant_scans if s.status == Scan.Status.COMPLETED
            )
            all_possible_scan_types = set(Scan.ScanType.values)
            
            if completed_scan_types == all_possible_scan_types:
                # Success case! All 6 scans are done.
                evaluation.status = Evaluation.Status.COMPLETED
                logger.info(f"Evaluation {evaluation_id} marked as COMPLETED (6/6 scans) and merged.")
                
                # Condition 1: All scans finished -> Generate metadata
                fetch_and_update_metadata(evaluation)
            else:
                # Partial case.
                evaluation.status = Evaluation.Status.IN_PROGRESS
                logger.info(f"Partial Evaluation merge {evaluation_id} complete. Stays IN_PROGRESS ({len(completed_scan_types)}/6).")
                        
            # --- 5. Save Changes ---
            # Save the merged JSON and the new status.
            evaluation.save()

    except Evaluation.DoesNotExist:
        logger.error(f"check_and_merge_evaluation: Evaluation {evaluation_id} not found.")
    except Exception as e:
        logger.error(f"Critical error merging evaluation {evaluation_id}: {e}", exc_info=True)
        # Fallback to fail the eval if the merge task itself errors
        try:
            eval_fail = Evaluation.objects.get(id=evaluation_id)
            if eval_fail.status != Evaluation.Status.COMPLETED:
                eval_fail.status = Evaluation.Status.FAILED
                eval_fail.error_message = f"Error during merge task: {e}"
                eval_fail.save()
        except Exception:
            pass
