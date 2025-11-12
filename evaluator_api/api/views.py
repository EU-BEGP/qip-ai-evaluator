from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from dateutil.parser import isoparse
import requests
import logging

from .models import User, Module, Evaluation, Scan
from .security import verify_rag_callback
from .tasks import check_and_merge_evaluation
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

# --- Helper Functions ---
def get_module_for_user(user: User, course_key: str) -> Module | None:
    try:
        module = Module.objects.get(user=user, course_key=course_key)
        return module
    except Module.DoesNotExist:
        return None

def get_rag_last_modified(course_key: str) -> str | None:
    """Calls the RAG API to get its last modified date."""
    try:
        response = requests.get(
            settings.RAG_API_MODULE_MODIFIED_URL,
            params={'course_key': course_key},
            timeout=5
        )
        response.raise_for_status()
        return response.json().get('last_modified_date')
    except requests.exceptions.RequestException as e:
        logger.error(f"Could not get last_modified_date from RAG API: {e}")
        return None

def build_results_json(evaluation: Evaluation) -> dict:
    """Builds the final merged JSON from an Evaluation's Scans."""
    content_list = []
    for scan in evaluation.scans.all():
        if scan.result_json:
             content_list.append(scan.result_json)
    return {
        "title": f"Evaluation for {evaluation.module.course_key}",
        "content": content_list
    }

# --- 0. Login Proxy Endpoint ---
@api_view(['POST'])
@permission_classes([AllowAny])
def login_proxy(request):
    email = request.data.get('email')
    password = request.data.get('password')
    if not email or not password:
        return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        response = requests.post(
            settings.EXTERNAL_LOGIN_API_URL, 
            data={'email': email, 'password': password},
            timeout=10
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in (401, 400):
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"error": f"Error from auth server: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except requests.exceptions.RequestException as e:
        return Response({"error": f"Could not connect to auth server: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    user, created = User.objects.get_or_create(email=email)
    if created:
        user.set_unusable_password()
        user.save()
    refresh = RefreshToken.for_user(user)
    return Response({ 'refresh': str(refresh), 'access': str(refresh.access_token), })

# --- 1. POST /evaluate ---
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def start_new_evaluation(request):
    course_key = request.data.get('course_key')
    email = request.data.get('email')
    scan_name = request.data.get('scan_name')

    if not course_key or not email or request.user.email != email:
        return Response({"error": "Invalid course_key or email, or token mismatch."}, status=status.HTTP_403_FORBIDDEN)
    
    module, _ = Module.objects.get_or_create(user=request.user, course_key=course_key)
    
    rag_last_modified_str = get_rag_last_modified(course_key)
    if not rag_last_modified_str:
        return Response({"error": "Could not contact RAG API to check module date."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    rag_last_modified_date = isoparse(rag_last_modified_str)
    scans_requested_now = [scan_name] if scan_name else list(Scan.ScanType.values)
    
    existing_eval = Evaluation.objects.filter(
        module=module,
        created_at=rag_last_modified_date 
    ).order_by('-updated_at').first()

    scans_to_run_now = []
    
    if existing_eval:
        # --- CACHE HIT (Partial or Full) ---
        
        # Exclude FAILED scans from the cache check so they can be re-run
        existing_scans_set = set(Scan.objects.filter(
            evaluation=existing_eval,
            scan_type__in=scans_requested_now
        ).exclude(status=Scan.Status.FAILED).values_list('scan_type', flat=True))
        
        scans_to_run_now = [s for s in scans_requested_now if s not in existing_scans_set]

        if not scans_to_run_now:
            # Full Cache Hit: All requested scans already exist (and are not FAILED).
            logger.info(f"Full cache hit for eval {existing_eval.id}. Requested scans already exist.")
            
            if scan_name:
                try:
                    scan_obj = Scan.objects.get(evaluation=existing_eval, scan_type=scan_name)
                    return Response(
                        { "message": "Scan already complete or in progress (cached).", "scan_id": scan_obj.id },
                        status=status.HTTP_200_OK
                    )
                except Scan.DoesNotExist:
                     return Response({"error": "Cache hit, but scan object not found."}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response(
                    { "message": "Evaluation already complete or in progress (cached).", "evaluation_id": existing_eval.id },
                    status=status.HTTP_200_OK
                )
        
        # Partial Cache Hit: Some scans are missing or failed.
        logger.info(f"Partial cache hit for eval {existing_eval.id}. Adding new scans: {scans_to_run_now}")
        existing_eval.requested_scans = list(set(existing_eval.requested_scans).union(set(scans_to_run_now)))
        existing_eval.status = Evaluation.Status.IN_PROGRESS
        existing_eval.result_json = None 
        existing_eval.save()
        
        evaluation_to_run = existing_eval 
        
    else:
        # --- CACHE MISS ---
        logger.info(f"Cache miss for course {course_key}. Starting new evaluation.")
        evaluation_to_run = Evaluation.objects.create(
            module=module,
            status=Evaluation.Status.IN_PROGRESS,
            requested_scans=scans_requested_now,
            created_at=rag_last_modified_date 
        )
        scans_to_run_now = scans_requested_now

    # --- 5. Create Placeholder Scan objects ---
    placeholder_scans = {}
    for s_name in scans_to_run_now:
        scan_obj, created = Scan.objects.get_or_create(
            evaluation=evaluation_to_run,
            scan_type=s_name
        )
        
        if not created and scan_obj.status == Scan.Status.FAILED:
            scan_obj.status = Scan.Status.IN_PROGRESS 
            scan_obj.result_json = None 
            scan_obj.save()
            
        placeholder_scans[s_name] = scan_obj

    # --- 6. Call the RAG API ---
    last_completed_eval = Evaluation.objects.filter(module=module, status=Evaluation.Status.COMPLETED).order_by('-created_at').first()
    previous_evaluation_json = last_completed_eval.result_json if last_completed_eval else None
    
    rag_payload = {
        "evaluation_id": evaluation_to_run.id,
        "course_key": module.course_key,
        "qip_user_id": str(request.user.id),
        "scan_names": scans_to_run_now, 
        "previous_evaluation": previous_evaluation_json,
    }

    try:
        response = requests.post(
            settings.RAG_API_EVALUATE_URL,
            json=rag_payload,
            timeout=10
        )
        response.raise_for_status()
        
        if response.status_code != status.HTTP_202_ACCEPTED:
            evaluation_to_run.status = Evaluation.Status.FAILED
            evaluation_to_run.error_message = "RAG API did not accept the task"
            evaluation_to_run.save()
            Scan.objects.filter(id__in=[s.id for s in placeholder_scans.values()]).update(status=Scan.Status.FAILED)
            return Response({"error": "RAG API did not accept the task"}, status=response.status_code)

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to call RAG API: {e}")
        evaluation_to_run.status = Evaluation.Status.FAILED
        evaluation_to_run.error_message = str(e)
        evaluation_to_run.save()
        Scan.objects.filter(id__in=[s.id for s in placeholder_scans.values()]).update(status=Scan.Status.FAILED)
        return Response({"error": f"Could not connect to RAG API: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- 7. Return the correct ID ---
    if scan_name:
        scan_to_return = placeholder_scans.get(scan_name)
        if not scan_to_return:
             scan_to_return = Scan.objects.get(evaluation=evaluation_to_run, scan_type=scan_name)

        return Response(
            { "message": "Scan started.", "scan_id": scan_to_return.id },
            status=status.HTTP_202_ACCEPTED
        )
    else:
        return Response(
            { "message": "Evaluation started.", "evaluation_id": evaluation_to_run.id },
            status=status.HTTP_202_ACCEPTED
        )

# --- 2. POST /list_evaluations (FIXED per your new logic) ---
@api_view(['POST']) 
@permission_classes([IsAuthenticated])
def list_evaluations(request):
    course_key = request.data.get('course_key')
    email = request.data.get('email')
    scan_name = request.data.get('scan_name') 

    if not course_key or not email or request.user.email != email:
        return Response({"error": "Invalid course_key or email, or token mismatch."}, status=status.HTTP_403_FORBIDDEN)

    module = get_module_for_user(request.user, course_key)
    if not module:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if scan_name:
        # Logic for a specific scan: Find all *Scans*
        scans = Scan.objects.filter(
            evaluation__module=module,
            scan_type=scan_name,
            status=Scan.Status.COMPLETED  # Only list completed ones
        ).select_related('evaluation').order_by('-evaluation__created_at')[:10]
        
        results = [
            {"id": scan.id, "date": scan.evaluation.formatted_date}
            for scan in scans
        ]
    else:
        # Logic for all evaluations for that module
        evaluations = Evaluation.objects.filter(
            module=module, 
            status=Evaluation.Status.COMPLETED, # Only list completed ones
        ).order_by('-created_at')[:10]
        
        results = [
            {"id": ev.id, "date": ev.formatted_date}
            for ev in evaluations
        ]
    
    if not results:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    return Response(results)

# --- 3. GET /evaluation_detail/module/<pk> ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_detail_module(request, pk):
    evaluation = get_object_or_404(Evaluation, pk=pk, module__user=request.user)
    if evaluation.status != Evaluation.Status.COMPLETED or not evaluation.result_json:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(evaluation.result_json)

# --- 4. GET /evaluation_detail/scan/<pk> ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_detail_scan(request, pk):
    scan = get_object_or_404(Scan, pk=pk, evaluation__module__user=request.user)
    
    if scan.status != Scan.Status.COMPLETED or not scan.result_json:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    return Response(scan.result_json)

# --- 5. GET /evaluation_status/module/<pk> ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_status_module(request, pk):
    evaluation = get_object_or_404(Evaluation, pk=pk, module__user=request.user)
    return Response({
        "status": evaluation.status,
        "course_key": evaluation.module.course_key,
        "scan_name": "All Scans"
    })

# --- 6. GET /evaluation_status/scan/<pk> ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_status_scan(request, pk):
    scan = get_object_or_404(Scan, pk=pk, evaluation__module__user=request.user)
    
    return Response({
        "status": scan.status, 
        "course_key": scan.evaluation.module.course_key,
        "scan_name": scan.scan_type
    })

# --- RAG API CALLBACK ---
@api_view(['POST'])
@verify_rag_callback
@transaction.atomic
def evaluation_callback(request):
    data = request.data
    evaluation_id = data.get('evaluation_id')
    
    try:
        evaluation = Evaluation.objects.get(id=int(evaluation_id), status=Evaluation.Status.IN_PROGRESS)
    except (Evaluation.DoesNotExist, TypeError, ValueError):
        logger.warning(f"Callback received for unknown or completed evaluation: {evaluation_id}")
        return Response({"message": "Evaluation not found or not in progress"}, status=status.HTTP_200_OK)

    callback_status = data.get('status')
    results_json = data.get('results')
    
    if callback_status == 'FAILED':
        evaluation.status = Evaluation.Status.FAILED
        evaluation.error_message = data.get('error')
        evaluation.save()
        evaluation.scans.filter(
            status__in=[Scan.Status.IN_PROGRESS, Scan.Status.PENDING]
        ).update(status=Scan.Status.FAILED)
        
    elif callback_status == 'COMPLETE' and results_json:
        all_possible_scans = set(Scan.ScanType.values)
        
        # **FIX:** This logic now saves the full JSON structure per scan
        callback_title = results_json.get('title', 'Evaluation')
        
        for scan_data in results_json.get('content', []):
            scan_type = scan_data.get('scan')
            if scan_type in all_possible_scans:
                
                # Create the full JSON structure for this *single scan*
                scan_specific_json = {
                    "title": callback_title,
                    "content": [scan_data] # Put the single scan in a content list
                }
                
                Scan.objects.update_or_create(
                    evaluation=evaluation,
                    scan_type=scan_type,
                    defaults={
                        'status': Scan.Status.COMPLETED,
                        'result_json': scan_specific_json # Save the full structure
                    }
                )
            else:
                logger.warning(f"Unknown scan type received: {scan_type}")
        
        check_and_merge_evaluation.delay(evaluation.id)
    
    else:
        evaluation.status = Evaluation.Status.FAILED
        evaluation.error_message = "Invalid callback or missing results"
        evaluation.save()
        evaluation.scans.filter(
            status__in=[Scan.Status.IN_PROGRESS, Scan.Status.PENDING]
        ).update(status=Scan.Status.FAILED)

    return Response({"message": "Callback processed"}, status=status.HTTP_200_OK)
