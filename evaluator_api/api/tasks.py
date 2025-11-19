from celery import shared_task
from django.db import transaction
import logging
from .models import Evaluation, Scan, Message

logger = logging.getLogger(__name__)

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
            
            # --- 2. Check if the current batch is still in progress ---
            # If any requested scans are still PENDING or IN_PROGRESS,
            # the batch isn't finished. Do nothing.
            in_progress_scans = evaluation.scans.filter(
                scan_type__in=requested_scan_types,
                status__in=[Scan.Status.PENDING, Scan.Status.IN_PROGRESS]
            ).exists()

            if in_progress_scans:
                logger.info(f"Evaluation {evaluation_id}: The current batch is still in progress.")
                return
            
            # --- 3. Merge JSON (Batch finished and did not fail) ---
            # Get *ALL* completed scans for this Evaluation,
            # not just the ones from this batch.
            
            all_completed_scans = evaluation.scans.filter(
                status=Scan.Status.COMPLETED
            ).order_by('scan_type')
            
            completed_scan_types = set(s.scan_type for s in all_completed_scans)
            
            final_content_list = []
            final_title = "" # Default title

            if all_completed_scans.exists():
                # 3a. Get the real title from the first valid scan
                for scan in all_completed_scans:
                    if scan.result_json and 'title' in scan.result_json:
                        final_title = scan.result_json['title']
                        if final_title:
                            break # Found a title, stop looping

                # 3b. Merge the *inner* content from EACH scan
                for scan in all_completed_scans:
                    if (scan.result_json and 
                        'content' in scan.result_json and 
                        isinstance(scan.result_json['content'], list)):
                        
                        # THE KEY LOGIC:
                        # Extend the main list with the *items* from the inner list
                        final_content_list.extend(scan.result_json['content'])
                    else:
                        logger.warning(f"Scan {scan.id} (type {scan.scan_type}) has malformed JSON, skipping from merge.")
            
            # 3c. Build the final JSON
            final_json = {
                "title": final_title,
                "content": final_content_list
            }
            evaluation.result_json = final_json
            
            # --- 4. Set Final Status (COMPLETED or IN_PROGRESS) ---
            
            # Compare the set of completed scans against *all* possible types
            all_possible_scan_types = set(Scan.ScanType.values)
            
            if completed_scan_types == all_possible_scan_types:
                # Success case! All 6 scans are done.
                evaluation.status = Evaluation.Status.COMPLETED
                logger.info(f"Evaluation {evaluation_id} marked as COMPLETED (6/6 scans) and merged.")
            else:
                # Partial case. The batch finished, but more scans are missing.
                # It stays IN_PROGRESS so more scans can be added later.
                evaluation.status = Evaluation.Status.IN_PROGRESS
                logger.info(f"Partial Evaluation merge {evaluation_id} complete. Stays IN_PROGRESS ({len(completed_scan_types)}/6).")
            
            # --- Create Notification Message if requested batch is done ---
            if requested_scan_types.issubset(completed_scan_types):
                module_title = final_title if final_title else evaluation.module.course_key
                
                if len(requested_scan_types) == len(all_possible_scan_types):
                     scan_text = "Full Evaluation"
                else:
                     scan_text = ", ".join(list(requested_scan_types))

                Message.objects.create(
                    user=evaluation.module.user,
                    title="Evaluation Completed",
                    content=f"The evaluation of module '{module_title}' for scan(s): {scan_text} has been completed.",
                    is_read=False
                )
            
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
