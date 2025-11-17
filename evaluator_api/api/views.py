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
            timeout=900
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
            timeout=900
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
    # 1. Input
    course_key = request.data.get('course_link') 
    email = request.data.get('email')
    scan_name = request.data.get('scan_name')

    if not course_key or not email or request.user.email != email:
        return Response({"error": "Invalid course_link or email, or token mismatch."}, status=status.HTTP_403_FORBIDDEN)
    
    # Validate scan_name if provided
    if scan_name and scan_name not in Scan.ScanType.values:
         return Response({"error": f"Invalid scan_name. Allowed: {Scan.ScanType.values}"}, status=status.HTTP_400_BAD_REQUEST)
    
    module, _ = Module.objects.get_or_create(user=request.user, course_key=course_key)
    
    rag_last_modified_str = get_rag_last_modified(course_key)
    if not rag_last_modified_str:
        return Response({"error": "Could not contact RAG API to check module date."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    rag_last_modified_date = isoparse(rag_last_modified_str)
    
    # If scan_name is empty, we request ALL scans
    scans_requested_now = [scan_name] if scan_name else list(Scan.ScanType.values)
    
    existing_eval = Evaluation.objects.filter(
        module=module,
        created_at=rag_last_modified_date 
    ).order_by('-updated_at').first()

    scans_to_run_now = []
    
    if existing_eval:
        # --- CACHE HIT LOGIC ---
        existing_scans_set = set(Scan.objects.filter(
            evaluation=existing_eval,
            scan_type__in=scans_requested_now
        ).exclude(status=Scan.Status.FAILED).values_list('scan_type', flat=True))
        
        scans_to_run_now = [s for s in scans_requested_now if s not in existing_scans_set]
        evaluation_to_run = existing_eval 

        if not scans_to_run_now:
            # Full Cache Hit: Everything is already done or processing
            logger.info(f"Full cache hit for eval {existing_eval.id}.")
            
            # Prepare response for Cache Hit
            response_data = {
                "message": "Evaluation already started/completed (cached).",
                "evaluation_id": existing_eval.id
            }
            
            if scan_name:
                # Return specific scan ID
                try:
                    scan_obj = Scan.objects.get(evaluation=existing_eval, scan_type=scan_name)
                    response_data["scan_id"] = scan_obj.id
                except Scan.DoesNotExist:
                     return Response({"error": "Cache hit, but scan object not found."}, status=status.HTTP_404_NOT_FOUND)
            else:
                # All scans requested -> scan_id equals evaluation_id
                response_data["scan_id"] = existing_eval.id

            return Response(response_data, status=status.HTTP_200_OK)
        
        # Partial Cache Hit
        logger.info(f"Partial cache hit for eval {existing_eval.id}. Adding new scans: {scans_to_run_now}")
        existing_eval.requested_scans = list(set(existing_eval.requested_scans).union(set(scans_to_run_now)))
        existing_eval.status = Evaluation.Status.IN_PROGRESS
        # We don't clear result_json here immediately to keep old results visible while new ones run
        existing_eval.save()
        
    else:
        logger.info(f"Cache miss for course {course_key}. Starting new evaluation.")
        evaluation_to_run = Evaluation.objects.create(
            module=module,
            status=Evaluation.Status.IN_PROGRESS,
            requested_scans=scans_requested_now,
            created_at=rag_last_modified_date 
        )
        scans_to_run_now = scans_requested_now

    # --- Create Placeholder Scan objects ---
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

    # --- Call the RAG API ---
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
            timeout=900
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

    # --- 7. Return the correct IDs  ---
    response_data = {
        "message": "Evaluation started.",
        "evaluation_id": evaluation_to_run.id
    }

    if scan_name:
        # Specific scan requested -> Return specific Scan ID
        scan_to_return = placeholder_scans.get(scan_name)
        if not scan_to_return:
             scan_to_return = Scan.objects.get(evaluation=evaluation_to_run, scan_type=scan_name)
        response_data["scan_id"] = scan_to_return.id
    else:
        # All scans requested -> scan_id = evaluation_id
        response_data["scan_id"] = evaluation_to_run.id

    return Response(response_data, status=status.HTTP_202_ACCEPTED)


# --- 2. POST /list_evaluations ---
@api_view(['POST']) 
@permission_classes([IsAuthenticated])
def list_evaluations(request):
    course_key = request.data.get('course_link')
    email = request.data.get('email')
    scan_name = request.data.get('scan_name') 

    if not course_key or not email or request.user.email != email:
        return Response({"error": "Invalid course_link or email, or token mismatch."}, status=status.HTTP_403_FORBIDDEN)

    module = get_module_for_user(request.user, course_key)
    if not module:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if scan_name and scan_name.lower() != "all scans":
        # Logic for a specific scan: Find all *Scans*
        # KEEP AS IS: Only return COMPLETED specific scans
        scans = Scan.objects.filter(
            evaluation__module=module,
            scan_type=scan_name,
            status=Scan.Status.COMPLETED 
        ).select_related('evaluation').order_by('-evaluation__created_at')[:10]
        
        results = [
            {"id": scan.id, "date": scan.evaluation.formatted_date}
            for scan in scans
        ]
    else:
        # Logic for all evaluations (History)
        evaluations = Evaluation.objects.filter(
            module=module, 
            status__in=[Evaluation.Status.COMPLETED, Evaluation.Status.IN_PROGRESS],
        ).order_by('-created_at')[:10]
        
        results = [
            {"id": ev.id, "date": ev.formatted_date}
            for ev in evaluations
        ]
    
    if not results:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    return Response(results)

# --- 3. GET /evaluation_detail/module/<pk> (MODIFIED) ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_detail_module(request, pk):
    evaluation = get_object_or_404(Evaluation, pk=pk, module__user=request.user)
    
    if evaluation.result_json:
        # Returns the merged JSON, even if the evaluation is IN_PROGRESS
        return Response(evaluation.result_json)
        
    if evaluation.status == Evaluation.Status.IN_PROGRESS:
        # The merge hasn't happened yet, tell the client to wait
        return Response(
            {"status": "IN_PROGRESS", "message": "Evaluation is running, final JSON is not merged yet."},
            status=status.HTTP_202_ACCEPTED
        )
        
    if evaluation.status == Evaluation.Status.COMPLETED and not evaluation.result_json:
         # This can happen if the merge fails or is delayed
         return Response({"status": "COMPLETED", "message": "Evaluation is complete but JSON is not yet available, please wait."}, status=status.HTTP_202_ACCEPTED)

    # The status is FAILED or NOT_STARTED
    return Response(status=status.HTTP_404_NOT_FOUND)

# --- 4. GET /evaluation_detail/scan/<pk> (MODIFIED) ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_detail_scan(request, pk):
    scan = get_object_or_404(Scan, pk=pk, evaluation__module__user=request.user)
    
    if scan.result_json:
        # --- THIS IS THE KEY ---
        # Returns the partial, growing JSON even if the status is IN_PROGRESS
        return Response(scan.result_json)
    
    if scan.status == Scan.Status.IN_PROGRESS:
        # It's running, but no criteria are complete yet
        return Response(
            {"status": "IN_PROGRESS", "message": "Scan is running, no criteria complete yet."},
            status=status.HTTP_202_ACCEPTED
        )
    
    # Status is FAILED, PENDING, or COMPLETED with no JSON
    return Response(status=status.HTTP_404_NOT_FOUND)

# --- 5. GET /evaluation_status/module/<pk> ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_status_module(request, pk):
    evaluation = get_object_or_404(Evaluation, pk=pk, module__user=request.user)
    
    # Default status map
    api_status = "Creating" # Default if Not Started or In Progress with no data

    # Logic to determine specific status based on your definitions
    if evaluation.status == Evaluation.Status.FAILED:
        api_status = "Failed"
    elif evaluation.status == Evaluation.Status.COMPLETED:
        api_status = "Completed"
    elif evaluation.status == Evaluation.Status.IN_PROGRESS:
        # Check if ANY scan has started producing results (Partial data exists)
        # If at least one criterion is evaluated, we consider it "In Progress"
        has_partial_results = evaluation.scans.exclude(result_json__isnull=True).exclude(result_json={}).exists()
        
        if has_partial_results:
            api_status = "In Progress"
        else:
            api_status = "Creating"

    return Response({
        "status": api_status,
        "course_key": evaluation.module.course_key,
        "scan_name": "All Scans", # Since this is module-level
        "evaluation_id": str(evaluation.id)
    })

# --- 6. GET /evaluation_status/scan/<pk> ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_status_scan(request, pk):
    scan = get_object_or_404(Scan, pk=pk, evaluation__module__user=request.user)
    
    api_status = "Creating"

    if scan.status == Scan.Status.FAILED:
        api_status = "Failed"
    elif scan.status == Scan.Status.COMPLETED:
        api_status = "Completed"
    elif scan.status == Scan.Status.IN_PROGRESS:
        # Check if THIS specific scan has JSON content
        if scan.result_json:
            api_status = "In Progress"
        else:
            api_status = "Creating"

    return Response({
        "status": api_status,
        "course_key": scan.evaluation.module.course_key,
        "scan_name": scan.scan_type,
        "evaluation_id": str(scan.evaluation.id)
    })

# --- 7. GET /link_module/<int:pk> ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_module_link(request, pk):
    """
    Returns the course link (course_key) for a specific module ID.
    """
    # Get the module, ensuring it belongs to the authenticated user
    module = get_object_or_404(Module, pk=pk, user=request.user)
    
    return Response({
        "course_link": module.course_key
    }, status=status.HTTP_200_OK)

# --- 8. GET /evaluation_ids/<int:pk> ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_evaluation_ids(request, pk):
    """
    Returns a list of all possible scans, their IDs (if generated),
    and whether they can be evaluated.
    """
    # 1. Get the requested Evaluation
    evaluation = get_object_or_404(Evaluation, pk=pk, module__user=request.user)

    # 2. Determine "Recency" (Is this the active/latest version?)
    # If there is a newer Evaluation object for this module, this one is 'History'.
    latest_eval = Evaluation.objects.filter(
        module=evaluation.module
    ).order_by('-created_at').first()
    
    is_recent = (latest_eval and evaluation.id == latest_eval.id)

    # 3. Get existing scans map
    existing_scans_map = {s.scan_type: s for s in evaluation.scans.all()}
    existing_scan_types = set(existing_scans_map.keys())
    all_possible_types = set(Scan.ScanType.values)

    response_list = []

    # 4. Logic for "All Scans" (Module Level) entry
    # Evaluable if: It is Recent AND Not all scans are completed yet
    are_scans_missing = len(existing_scan_types) < len(all_possible_types)
    
    response_list.append({
        "name": "All Scans",
        "id": evaluation.id, # The ID of the module evaluation itself
        "evaluable": is_recent and are_scans_missing
    })

    # 5. Iterate through individual Scan Types
    for scan_type_name in Scan.ScanType.values:
        scan_obj = existing_scans_map.get(scan_type_name)
        
        if scan_obj:
            # Case A: Scan already exists
            item = {
                "name": scan_type_name,
                "id": scan_obj.id,
                "evaluable": False # Already exists
            }
        else:
            # Case B: Scan does not exist (ID is null)
            # Evaluable ONLY if this is the recent version
            item = {
                "name": scan_type_name,
                "id": None,
                "evaluable": is_recent
            }
        
        response_list.append(item)

    return Response(response_list, status=status.HTTP_200_OK)

# --- 9. GET /modules/<email> ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_modules(request, email):
    """
    Returns a summary list of all modules belonging to the user email.
    Includes title, dates, and calculated average score (0-100).
    """
    if request.user.email != email:
        return Response({"error": "You can only list your own modules."}, status=status.HTTP_403_FORBIDDEN)

    modules = Module.objects.filter(user__email=email)
    response_list = []

    for mod in modules:
        # 1. Find the LATEST evaluation (Even if IN_PROGRESS)
        #    We exclude 'NOT_STARTED' only.
        latest_eval = Evaluation.objects.filter(
            module=mod
        ).exclude(
            status=Evaluation.Status.NOT_STARTED
        ).order_by('-updated_at').first()

        # 2. Last Modify (From Learnify via RAG API)
        rag_last_modified_str = get_rag_last_modified(mod.course_key)
        
        learnify_date_formatted = "N/A"
        if rag_last_modified_str:
            try:
                learnify_date_formatted = isoparse(rag_last_modified_str).strftime("%Y-%m-%d")
            except Exception:
                learnify_date_formatted = rag_last_modified_str

        module_data = {
            "title": mod.title if mod.title else "Pending Evaluation...", 
            "link": mod.course_key,
            "last_modify": learnify_date_formatted,
            "last_evaluation": "N/A",
            "last_average": 0,
            "last_max": 100
        }

        if latest_eval:
            # A. Update Date (Shows when it was last worked on)
            module_data["last_evaluation"] = latest_eval.updated_at.strftime("%Y-%m-%d")

            # B. Title Fallback
            if not mod.title and latest_eval.title:
                 module_data["title"] = latest_eval.title

            # C. Robust Average Calculation
            total_score = 0.0
            criteria_count = 0

            if latest_eval.result_json:
                # OPTION A: FAST - Read from final JSON
                content = latest_eval.result_json.get("content", [])
                if isinstance(content, list):
                    for scan_data in content:
                        for criterion in scan_data.get("criteria", []):
                            score = criterion.get("score", 0.0)
                            total_score += score
                            criteria_count += 1
            else:
                # OPTION B: REAL-TIME - Read from Scans DB (If JSON not ready yet)
                scans = latest_eval.scans.exclude(result_json__isnull=True)
                for scan in scans:
                    # Each scan result_json has "content": [{ "criteria": [...] }]
                    scan_content = scan.result_json.get("content", [])
                    if isinstance(scan_content, list) and len(scan_content) > 0:
                        # Usually partial JSON has 1 item in content
                        for criterion in scan_content[0].get("criteria", []):
                            score = criterion.get("score", 0.0)
                            total_score += score
                            criteria_count += 1

            if criteria_count > 0:
                average_5_scale = total_score / criteria_count
                module_data["last_average"] = int((average_5_scale / 5.0) * 100)

        response_list.append(module_data)

    return Response(response_list, status=status.HTTP_200_OK)

# --- RAG API CALLBACK ---
@api_view(['POST'])
@verify_rag_callback
@transaction.atomic
def evaluation_callback(request):
    data = request.data
    evaluation_id = data.get('evaluation_id')
    
    try:
        # Lock the evaluation row for this transaction
        evaluation = Evaluation.objects.select_for_update().get(id=int(evaluation_id))
    except (Evaluation.DoesNotExist, TypeError, ValueError):
        logger.warning(f"Callback received for unknown evaluation: {evaluation_id}")
        return Response({"message": "Evaluation not found"}, status=status.HTTP_200_OK)

    # If eval is already done, ignore new callbacks
    if evaluation.status in [Evaluation.Status.COMPLETED, Evaluation.Status.FAILED]:
        logger.warning(f"Callback received for already-finished evaluation: {evaluation_id}")
        return Response({"message": "Evaluation already finished"}, status=status.HTTP_200_OK)

    callback_status = data.get('status')
    results_json = data.get('results')
    
    # --- NEW: Handle Interim Updates ---
    if callback_status == 'CRITERION_COMPLETE':
        interim_result_json = data.get('interim_result')
        
        # Validate the received JSON
        if not interim_result_json or 'content' not in interim_result_json or not interim_result_json['content']:
            logger.warning(f"[{evaluation_id}] Invalid interim callback: missing or malformed 'interim_result'")
            return Response({"error": "Invalid interim_result"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Extract scan name from the JSON
            scan_name = interim_result_json['content'][0].get('scan')
            if not scan_name:
                 logger.warning(f"[{evaluation_id}] Interim JSON missing scan name in content[0]")
                 return Response({"error": "Interim JSON missing scan name"}, status=status.HTTP_400_BAD_REQUEST)

            # Get the Scan object
            scan_obj = Scan.objects.get(evaluation=evaluation, scan_type=scan_name)
            
            # --- THIS IS THE KEY ---
            # Overwrite the DB field with the new, bigger JSON
            scan_obj.result_json = interim_result_json
            scan_obj.save()
            
            logger.info(f"[{evaluation_id}] Saved interim result for scan: {scan_name}")
            return Response({"message": "Interim callback processed"}, status=status.HTTP_200_OK)

        except Scan.DoesNotExist:
             logger.warning(f"[{evaluation_id}] Interim callback for unknown scan: {scan_name}")
             return Response({"error": "Scan not found"}, status=status.HTTP_404_NOT_FOUND)
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"[{evaluation_id}] Failed to parse interim JSON: {e}")
            return Response({"error": "Failed to parse interim JSON"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- EXISTING: Handle Final Statuses ---
    elif callback_status == 'FAILED':
        evaluation.status = Evaluation.Status.FAILED
        evaluation.error_message = data.get('error')
        evaluation.save()
        evaluation.scans.filter(
            status__in=[Scan.Status.IN_PROGRESS, Scan.Status.PENDING]
        ).update(status=Scan.Status.FAILED)
        
    elif callback_status == 'COMPLETE' and results_json:
        all_possible_scans = set(Scan.ScanType.values)
        
        # This logic is the same as before
        callback_title = results_json.get('title', 'Evaluation')
        
        # --- UPDATE TITLES  ---
        if callback_title:
            # 1. Save to Evaluation (History)
            evaluation.title = callback_title
            # 2. Save to Module (Current State)
            evaluation.module.title = callback_title
            evaluation.module.save()
        
        for scan_data in results_json.get('content', []):
            scan_type = scan_data.get('scan')
            if scan_type in all_possible_scans:
                
                # Create the final JSON for this *single scan*
                scan_specific_json = {
                    "title": callback_title,
                    "content": [scan_data] # Put the single scan in a content list
                }
                
                # Overwrites the partial JSON, fixing title/description
                Scan.objects.update_or_create(
                    evaluation=evaluation,
                    scan_type=scan_type,
                    defaults={
                        'status': Scan.Status.COMPLETED,
                        'result_json': scan_specific_json
                    }
                )
            else:
                logger.warning(f"Unknown scan type received: {scan_type}")
        
        # Save evaluation with new status and title
        evaluation.save()
        
        # Call the *final* merge task
        check_and_merge_evaluation.delay(evaluation.id)
    
    else:
        evaluation.status = Evaluation.Status.FAILED
        evaluation.error_message = "Invalid final callback or missing results"
        evaluation.save()
        evaluation.scans.filter(
            status__in=[Scan.Status.IN_PROGRESS, Scan.Status.PENDING]
        ).update(status=Scan.Status.FAILED)

    return Response({"message": "Final callback processed"}, status=status.HTTP_200_OK)
