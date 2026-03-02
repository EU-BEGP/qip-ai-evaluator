# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import requests
import logging
from django.conf import settings
from django.utils import timezone
from .models import Module, Evaluation, Scan, UserModule, Rubric, Criterion
from apps.notifications.models import Message
from dateutil.parser import isoparse
import datetime
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

class RagService:
    # Encapsulates communication with the external RAG API
    
    @staticmethod
    def get_last_modified(course_key):
        try:
            response = requests.get(
                settings.RAG_API_MODULE_MODIFIED_URL,
                params={'course_key': course_key},
                timeout=900
            )
            response.raise_for_status()
            date_str = response.json().get('last_modified_date')
            if not date_str: return None
            dt = isoparse(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt
        except Exception as e:
            logger.error(f"RAG API Error: {e}")
            return None

    @staticmethod
    def trigger_evaluation(payload):
        # Dispatches the evaluation task to the RAG system
        try:
            response = requests.post(
                settings.RAG_API_EVALUATE_URL,
                json=payload,
                timeout=900
            )
            response.raise_for_status()
            return response.status_code
        except requests.exceptions.RequestException as e:
            logger.error(f"RAG API Error (Trigger Evaluation): {e}")
            raise e
        
    @staticmethod
    def trigger_single_suggestion(payload):
        # Dispatches the suggestion request to RAG. Returns JSON and Status Code.
        try:
            response = requests.post(
                settings.RAG_API_SUGGESTION_URL,
                json=payload,
                timeout=60 
            )
            return response.json(), response.status_code
        except requests.exceptions.RequestException as e:
            logger.error(f"RAG API Error (Trigger Suggestion): {e}")
            return {"error": "Failed to reach RAG service"}, 503
        
    @staticmethod
    def validate_metadata(payload):
        # Call to validate metadata fields
        try:
            url = getattr(settings, 'RAG_API_VALIDATE_METADATA_URL', None)
            if not url: return {"error": "Validation URL Config Error"}, 500
            
            response = requests.post(url, json=payload, timeout=60)
            return response.json(), response.status_code
        except Exception as e:
            logger.error(f"RAG Validation Error: {e}")
            return {"error": "RAG Service Unreachable"}, 503

class EvaluationService:
    # Business logic for managing modules and evaluations
    @staticmethod
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

    @staticmethod
    def get_valid_scan_types(rubric=None):
        if not rubric:
            rubric = Rubric.objects.first() 
        return rubric.available_scans if rubric else []
    
    @staticmethod
    def ensure_module_access(user, course_key):
        clean_key = course_key.split('?')[0]
        module, _ = Module.objects.get_or_create(course_key=clean_key)
        UserModule.objects.update_or_create(user=user, module=module)
        return module

    @staticmethod
    def get_running_evaluation(module):
        return Evaluation.objects.filter(
            module=module,
            status=Evaluation.Status.IN_PROGRESS
        ).order_by('-created_at').first()

    @staticmethod
    def get_cached_evaluation(module, rag_date):
        return Evaluation.objects.filter(
            module=module,
            created_at=rag_date
        ).order_by('-updated_at').first()

    @staticmethod
    def calculate_score_from_json(scan_result_json):
        # Calculates the average score from the evaluation JSON.
        if not scan_result_json:
            return 0.0, 0
            
        total_score = 0.0
        count = 0

        content = scan_result_json.get("content", [])
        if isinstance(content, list):
            for item in content:
                for criterion in item.get("criteria", []):
                    try:
                        score = float(criterion.get("score", 0))
                        total_score += score
                        count += 1
                    except (ValueError, TypeError):
                        continue
                        
        return total_score, count

    @staticmethod
    def get_user_dashboard_modules(user):
        return Module.objects.filter(
            followed_by__user=user
        ).order_by('-followed_by__last_accessed')
    

    @staticmethod
    def prepare_scans_and_placeholders(evaluation, requested_scan_name, user):
        active_rubric = evaluation.rubric
        available_scan_types = active_rubric.available_scans
        
        # 1. Normalize name to handle "all scans"
        scan_name_lower = str(requested_scan_name).lower().strip() if requested_scan_name else ""
        is_all_scans = (scan_name_lower == 'all scans' or not requested_scan_name)
        
        target_scans = available_scan_types if is_all_scans else [requested_scan_name]

        # 2. Filter completed scans
        completed_scans = set(Scan.objects.filter(
            evaluation=evaluation, 
            scan_type__in=target_scans,
            status=Scan.Status.COMPLETED
        ).values_list('scan_type', flat=True))

        scans_to_run = [s for s in target_scans if s not in completed_scans]

        # 3. Handle IDs (Ensure no nulls)
        partial_scan_id = None
        if not is_all_scans:
            scan_obj, _ = Scan.objects.get_or_create(
                evaluation=evaluation, 
                scan_type=requested_scan_name,
                defaults={'status': Scan.Status.PENDING}
            )
            partial_scan_id = str(scan_obj.id)
        
        # 4. Status Management Rules
        if scans_to_run:
            for stype in scans_to_run:
                Scan.objects.get_or_create(evaluation=evaluation, scan_type=stype)

            Scan.objects.filter(
                evaluation=evaluation,
                scan_type__in=scans_to_run
            ).update(status=Scan.Status.IN_PROGRESS)
            
            evaluation.requested_scans = list(set((evaluation.requested_scans or []) + scans_to_run))
            
            # Only All Scans triggers IN_PROGRESS on the evaluation level
            if is_all_scans:
                evaluation.status = Evaluation.Status.IN_PROGRESS
            else:
                evaluation.status = Evaluation.Status.INCOMPLETED
            
            evaluation.triggered_by = user
            evaluation.save()

        return scans_to_run, partial_scan_id, is_all_scans

    @staticmethod
    def merge_scan_results(evaluation, new_content_list, save=True):
        # Centralized logic to merge new scan results into the evaluation JSON
        current_json = evaluation.result_json or {"title": evaluation.title, "content": []}
        current_content = current_json.get("content", [])
        
        content_map = {item.get('scan'): item for item in current_content}

        for new_item in new_content_list:
            scan_type = new_item.get('scan')
            if scan_type:
                content_map[scan_type] = new_item 

        merged_content = list(content_map.values())
        
        # Preserve title logic
        final_title = evaluation.title
        if not final_title and current_json.get('title'):
            final_title = current_json.get('title')

        evaluation.result_json = {
            "title": final_title,
            "content": merged_content
        }
        
        if save:
            evaluation.save()

    @staticmethod
    def handle_evaluation_completion(evaluation, result_payload):
        # 1. Update Title if provided
        if result_payload.get('title'):
            evaluation.title = result_payload['title']
            if evaluation.module:
                evaluation.module.title = result_payload['title']
                evaluation.module.save()

        # 2. Update ONLY the scans that are actually present in this payload
        valid_types = EvaluationService.get_valid_scan_types(evaluation.rubric)
        new_content = result_payload.get('content', [])

        for scan_data in new_content:
            s_name = scan_data.get('scan')
            if s_name in valid_types:
                Scan.objects.update_or_create(
                    evaluation=evaluation, scan_type=s_name,
                    defaults={
                        'status': Scan.Status.COMPLETED,
                        'result_json': {"title": evaluation.title, "content": [scan_data]}
                    }
                )
                
                # Notification
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

        # 3. Merge ONLY the new content into the global JSON
        EvaluationService.merge_scan_results(evaluation, new_content, save=False)
        EvaluationService.check_and_update_status(evaluation)

    @staticmethod
    def check_and_update_status(evaluation):
        # Checks if all scans have finished and updates Evaluation status
        completed_types = set(
            evaluation.scans.filter(status=Scan.Status.COMPLETED).values_list('scan_type', flat=True)
        )
        all_possible_types = set(EvaluationService.get_valid_scan_types(evaluation.rubric))
        if all_possible_types.issubset(completed_types):
            evaluation.status = Evaluation.Status.COMPLETED
        else:
            evaluation.status = Evaluation.Status.INCOMPLETED
        evaluation.save()
    
    @staticmethod
    def get_or_create_evaluation_structure(module, user):
        # Initialize evaluation or get last one
        active_rubric = Rubric.objects.first()
        if not active_rubric:
            raise ValueError("No active rubric found.")
        latest_eval = Evaluation.objects.filter(module=module).order_by('-created_at').first()
        rag_date = RagService.get_last_modified(module.course_key)
        should_create_new = False

        if not latest_eval:
            should_create_new = True
        else:
            # Rubric is outdated
            if latest_eval.status in [Evaluation.Status.NOT_STARTED, Evaluation.Status.SELF_ASSESSMENT]:
                if latest_eval.rubric != active_rubric:
                    should_create_new = True
            
            # Check if module is outdated
            else:
                if rag_date and rag_date.replace(second=0, microsecond=0) > latest_eval.created_at.replace(second=0, microsecond=0):
                    should_create_new = True

        # Must return last evaluation if other cases do not apply
        if not should_create_new:
            return latest_eval, False

        # Create new evaluation
        evaluation = Evaluation.objects.create(
            module=module,
            triggered_by=user,
            rubric=active_rubric,
            status=Evaluation.Status.SELF_ASSESSMENT,
            requested_scans=[], 
            created_at=timezone.now(),
            title=module.title or "New Evaluation"
        )

        # Retrieve metadata for evaluation
        try:
            EvaluationService.fetch_and_update_metadata(evaluation)
            evaluation.refresh_from_db()
            # Create title for the evaluation
            if evaluation.metadata_json and 'title' in evaluation.metadata_json:
                new_title = evaluation.metadata_json['title']
                evaluation.title = new_title
                module.title = new_title
                module.save()
                evaluation.save()
        except Exception as e:
            logger.error(f"Immediate metadata fetch failed for Eval {evaluation.id}: {e}")

        # Create scans
        valid_scans = active_rubric.available_scans
        scans_objs = [
            Scan(evaluation=evaluation, scan_type=st, status=Scan.Status.PENDING) 
            for st in valid_scans
        ]
        created_scans = Scan.objects.bulk_create(scans_objs)
        
        # Create criteria
        criteria_objs = []
        rubric_content = active_rubric.content if isinstance(active_rubric.content, list) else [] 
        rubric_map = {
            item.get('scan'): item.get('criteria', []) 
            for item in rubric_content if item.get('scan')
        }
        for scan_instance in created_scans:
            scan_def = rubric_map.get(scan_instance.scan_type, [])
            for crit_def in scan_def:
                criteria_objs.append(Criterion(
                    scan=scan_instance,
                    criterion_name=crit_def.get('name'),
                    status="Pending"
                ))       
        if criteria_objs:
            Criterion.objects.bulk_create(criteria_objs)
        
        return evaluation, True
    
    @staticmethod
    def get_self_assessment_results(evaluation_id):
        # Calculates the distribution of user answers across all scans
        evaluation = get_object_or_404(Evaluation, pk=evaluation_id)
    
        # 1. Extract scan descriptions
        scan_descriptions = {}
        if evaluation.rubric and evaluation.rubric.content:
            content = evaluation.rubric.content
            if isinstance(content, list):
                for s in content:
                    if isinstance(s, dict) and 'scan' in s:
                        scan_descriptions[s['scan']] = s.get('description', '')
            elif isinstance(content, dict):
                scans_dict = content.get('scans', {})
                if isinstance(scans_dict, dict):
                    for k, v in scans_dict.items():
                        if isinstance(v, dict):
                            scan_descriptions[k] = v.get('description', '')

        # 2. Consult all scans
        scans = evaluation.scans.prefetch_related('criteria_results').all()
        all_scans_dist = {"yes": 0, "no": 0, "not_applicable": 0, "unanswered": 0, "total": 0}
        results = []
        
        # 3. Calculate distribution of answers
        for scan in scans:
            dist = {"yes": 0, "no": 0, "not_applicable": 0, "unanswered": 0, "total": 0}
            criteria = scan.criteria_results.all()
            
            for c in criteria:
                dist["total"] += 1
                all_scans_dist["total"] += 1
                
                sel = c.user_selection
                if sel == 'YES':
                    dist["yes"] += 1
                    all_scans_dist["yes"] += 1
                elif sel == 'NO':
                    dist["no"] += 1
                    all_scans_dist["no"] += 1
                elif sel == 'NOT APPLICABLE':
                    dist["not_applicable"] += 1
                    all_scans_dist["not_applicable"] += 1
                else:
                    dist["unanswered"] += 1
                    all_scans_dist["unanswered"] += 1
            results.append({
                "name": scan.scan_type,
                "description": scan_descriptions.get(scan.scan_type, ""),
                "answer_distribution": dist
            })
            
        # 4. All scans case
        all_scans_block = {
            "name": "All Scans",
            "description": "All scans have been consolidated here, and the information provided offers a general overview of the module.",
            "answer_distribution": all_scans_dist
        }
        return [all_scans_block] + results
    
    @staticmethod
    def get_self_assessment_completion_status(evaluation_id):
        # Verifica si todos los criterios de cada scan han sido respondidos
        from django.shortcuts import get_object_or_404
        from .models import Evaluation
        
        evaluation = get_object_or_404(Evaluation, pk=evaluation_id)
        scans = evaluation.scans.prefetch_related('criteria_results').all()
        
        scan_complete_list = []
        
        for scan in scans:
            criteria = scan.criteria_results.all()
            if not criteria:
                scan_complete_list.append({
                    "name": scan.scan_type, 
                    "isComplete": False
                })
            else:
                is_complete = all(bool(c.user_selection) for c in criteria)
                scan_complete_list.append({
                    "name": scan.scan_type, 
                    "isComplete": is_complete
                })
                
        return {"scanComplete": scan_complete_list}
