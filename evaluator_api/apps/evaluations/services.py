import requests
import logging
from django.conf import settings
from django.utils import timezone
from .models import Module, Evaluation, Scan, UserModule

logger = logging.getLogger(__name__)

class RagService:
    # Encapsulates communication with the external RAG API
    
    @staticmethod
    def get_last_modified(course_key):
        # Fetches metadata from RAG service
        try:
            response = requests.get(
                settings.RAG_API_MODULE_MODIFIED_URL,
                params={'course_key': course_key},
                timeout=900
            )
            response.raise_for_status()
            return response.json().get('last_modified_date')
        except requests.exceptions.RequestException as e:
            logger.error(f"RAG API Error (Last Modified): {e}")
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

class EvaluationService:
    # Business logic for managing modules and evaluations
    
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
    def resolve_evaluation_instance(module, user, rag_date, input_id=None, requested_scan_name=None):
        # Decides whether to reuse an existing evaluation or create new one

        # 1. Case: specific ID provided (Retry/Validate)
        if input_id:
            try:
                target_eval = Evaluation.objects.get(id=input_id, module=module)
                db_date = target_eval.created_at.replace(second=0, microsecond=0)
                live_date = rag_date.replace(second=0, microsecond=0)

                if db_date != live_date:
                    raise ValueError(f"Evaluation outdated. Current: {live_date}, Provided: {db_date}")
                
                return target_eval, False
            except Evaluation.DoesNotExist:
                raise LookupError("Evaluation ID not found.")

        # 2. Case: Auto-discovery (Cache vs New)
        cached_eval = EvaluationService.get_cached_evaluation(module, rag_date)
        if cached_eval:
            return cached_eval, False

        # 3. Create New
        initial_scans = [requested_scan_name] if (requested_scan_name and requested_scan_name.lower() != "all scans") else list(Scan.ScanType.values)
        
        new_eval = Evaluation.objects.create(
            module=module,
            triggered_by=user,
            status=Evaluation.Status.IN_PROGRESS,
            requested_scans=initial_scans,
            created_at=rag_date
        )
        return new_eval, True

    @staticmethod
    def prepare_scans_and_placeholders(evaluation, requested_scan_name, user):
        # Determines which scans actually need to run

        # 1. Determine scope
        if not requested_scan_name or requested_scan_name.lower() == "all scans":
            scans_scope = list(Scan.ScanType.values)
            is_all_scans = True
        else:
            scans_scope = [requested_scan_name]
            is_all_scans = False

        # 2. Filter out already completed scans (Delta Logic)
        existing_scans_set = set(evaluation.scans.exclude(status=Scan.Status.FAILED).values_list('scan_type', flat=True))
        scans_to_run = [s for s in scans_scope if s not in existing_scans_set]

        if not scans_to_run:
            return [], [], is_all_scans

        # 3. Update History & Authorship (Last Modified By)
        current_requested = set(evaluation.requested_scans)
        current_requested.update(scans_to_run)
        evaluation.requested_scans = list(current_requested)
        evaluation.triggered_by = user 
        evaluation.status = Evaluation.Status.IN_PROGRESS
        evaluation.save()

        created_objs = []
        for s_name in scans_to_run:
            scan_obj, _ = Scan.objects.update_or_create(
                evaluation=evaluation, 
                scan_type=s_name, 
                defaults={
                    'status': Scan.Status.IN_PROGRESS,
                    'result_json': None
                }
            )
            created_objs.append(scan_obj)
            
        return scans_to_run, created_objs, is_all_scans
