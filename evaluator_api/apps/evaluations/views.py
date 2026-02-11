# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
import datetime
from dateutil.parser import isoparse
import logging
import tempfile
import os
import json

from .models import Module, Evaluation, Scan, UserModule, Rubric, Criterion
from .serializers import StartEvaluationSerializer, EvaluationDetailSerializer, CriterionListSerializer, CriterionUpdateSerializer
from .services import EvaluationService, RagService
from evaluation.report_manager import ReportManager 
from .security import verify_rag_callback 

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def start_evaluation(request):
    # Orchestrates evaluation process: validates, reuses/creates instance, triggers RAG
    serializer = StartEvaluationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    user = request.user
    course_link = data.get('course_link')

    # 1. Get module link
    clean_key = course_link.split('?')[0]
    module = get_object_or_404(Module, course_key=clean_key)

    # 2. Retrieve Evaluation
    evaluation = Evaluation.objects.filter(module=module).order_by('-created_at').first()
    
    if not evaluation:
        return Response(
            {"error": "No evaluation found for this module. Create one first."}, 
            status=status.HTTP_404_NOT_FOUND
        )
    if evaluation.status == Evaluation.Status.COMPLETED:
        return Response(
            {"error": "Evaluation already completed. Cannot restart."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # 3. Prepare Scans
    scans_to_run, partial_id, is_all = EvaluationService.prepare_scans_and_placeholders(
        evaluation, request.data.get('scan_name'), request.user
    )
    final_scan_id = str(evaluation.id) if is_all else partial_id

    if not scans_to_run:
        return Response({
            "message": "All requested scans are already completed.",
            "evaluation_id": str(evaluation.id),
            "scan_id": final_scan_id
        }, status=status.HTTP_200_OK)
    
    if evaluation.module_last_modified is None:
        rag_date = RagService.get_last_modified(module.course_key)
        if rag_date:
            evaluation.module_last_modified = rag_date
        evaluation.save(update_fields=['module_last_modified'])

    # 4. Trigger RAG
    payload = {
        "evaluation_id": evaluation.id,
        "course_key": evaluation.module.course_key,
        "callback_url": f"{settings.SERVER_PUBLIC_URL.rstrip('/')}{reverse('evaluation_callback')}",
        "qip_user_id": str(user.id),
        "scan_names": scans_to_run, 
        "existing_snapshot": evaluation.document_snapshot
    }
    
    try:
        RagService.trigger_evaluation(payload)
    except Exception as e:
        evaluation.status = Evaluation.Status.FAILED
        evaluation.save()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 5. Response
    return Response({
        "message": "Evaluation started.", 
        "evaluation_id": str(evaluation.id),
        "scan_id": final_scan_id
    }, status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_evaluation_ids(request, pk):
    # Returns status/evaluability of all scans; checks for outdated content
    evaluation = get_object_or_404(Evaluation, pk=pk)
    
    rag_date = RagService.get_last_modified(evaluation.module.course_key)
    is_outdated = False

    # 1. Check if this evaluation is the most recent one in the DB
    latest_local = Evaluation.objects.filter(module=evaluation.module).order_by('-created_at').first()
    if latest_local and latest_local.id != evaluation.id:
        is_outdated = True
    # 2. If it is the latest, check if the module content in Learnify is newer
    elif rag_date and rag_date.replace(second=0, microsecond=0) > evaluation.created_at.replace(second=0, microsecond=0):
        is_outdated = True

    active_scans = set(evaluation.scans.filter(status__in=[Scan.Status.IN_PROGRESS, Scan.Status.COMPLETED]).values_list('scan_type', flat=True))
    expected_scans_list = EvaluationService.get_valid_scan_types(evaluation.rubric)
    expected_scans_set = set(expected_scans_list)
    missing_scans = expected_scans_set - active_scans
    existing_scans_map = {s.scan_type: s for s in evaluation.scans.all()}
    response_list, global_total, global_count = [], 0.0, 0
    scans_data = []

    for s_type in expected_scans_list:
        scan = existing_scans_map.get(s_type)
        s_id, s_status, s_avg, s_evaluable = None, "Not Started", None, True
        
        if scan:
            s_id, s_status = scan.id, scan.status
            if s_status in [Scan.Status.IN_PROGRESS, Scan.Status.COMPLETED]: s_evaluable = False
            if scan.result_json:
                total, count = EvaluationService.calculate_score_from_json(scan.result_json)
                if count > 0:
                    s_avg = round(total/count, 2)
                    global_total += total; global_count += count
        
        if is_outdated: s_evaluable = False
        scans_data.append({
            "name": s_type,
            "id": s_id, 
            "evaluable": s_evaluable, 
            "scan_max": 5.0, 
            "scan_average": s_avg, 
            "status": s_status, 
            "outdated": is_outdated
        })

    global_avg = round(global_total/global_count, 2) if global_count > 0 else None
    response_list.append({
        "name": "All Scans", 
        "id": evaluation.id, 
        "evaluable": (len(missing_scans) > 0 and not is_outdated),
        "scan_max": 5.0, 
        "scan_average": global_avg, 
        "status": evaluation.status,
        "outdated": is_outdated
    })
    response_list.extend(scans_data)
    return Response(response_list, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_module_link(request, pk):
    # Returns course link securely (owner or dashboard follower)
    evaluation = get_object_or_404(Evaluation, pk=pk)
    has_access = (evaluation.triggered_by == request.user) or \
                 UserModule.objects.filter(user=request.user, module=evaluation.module).exists()

    if not has_access:
        return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
    return Response({"course_link": evaluation.module.course_key}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_detail_module(request, pk):
    # Returns full evaluation JSON; supports polling
    evaluation = get_object_or_404(Evaluation, pk=pk)
    if evaluation.status not in [Evaluation.Status.IN_PROGRESS, Evaluation.Status.INCOMPLETED, Evaluation.Status.COMPLETED]:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if evaluation.result_json: return Response(evaluation.result_json)
    return Response({"status": "IN_PROGRESS"}, status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_detail_scan(request, pk):
    # Returns specific scan JSON; supports polling
    scan = get_object_or_404(Scan, pk=pk)
    if scan.status not in [Scan.Status.IN_PROGRESS, Scan.Status.COMPLETED]:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if scan.result_json: return Response(scan.result_json)
    return Response({"status": "IN_PROGRESS"}, status=status.HTTP_202_ACCEPTED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def list_evaluations(request):
    # Lists history by Last Modified
    course_key = request.data.get('course_link')
    if not course_key: return Response(status=status.HTTP_400_BAD_REQUEST)
    
    try: module = Module.objects.get(course_key=course_key)
    except Module.DoesNotExist: return Response(status=status.HTTP_404_NOT_FOUND)

    evals = Evaluation.objects.filter(module=module).order_by('-created_at')[:20]
    
    if not evals.exists(): return Response(status=status.HTTP_404_NOT_FOUND)

    data = [{
        "id": e.id, 
        "date": e.created_at.strftime("%Y-%m-%d %H:%M"), 
        "user": e.triggered_by.email if e.triggered_by else "System"
    } for e in evals]
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_status_module(request, pk):
    # Returns UI status for Evaluation (Creating/In Progress/etc)
    evaluation = get_object_or_404(Evaluation, pk=pk)
    return Response({
        "status": evaluation.status, "course_key": evaluation.module.course_key,
        "scan_name": "All Scans", "evaluation_id": str(evaluation.id)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evaluation_status_scan(request, pk):
    # Returns UI status for Scan
    scan = get_object_or_404(Scan, pk=pk)
    return Response({
        "status": scan.status, "course_key": scan.evaluation.module.course_key,
        "scan_name": scan.scan_type, "evaluation_id": str(scan.evaluation.id)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_modules(request, email):
    # Returns the list of modules for a specific user; determines status (Outdated, Updated, Self assessment)
    user_modules = UserModule.objects.filter(user__email=email).select_related('module')
    response_data = []

    for um in user_modules:
        module = um.module
        last_eval = Evaluation.objects.filter(module=module).order_by('-created_at').first()
        
        last_modify = None
        last_evaluation_date = None
        last_avg = None
        last_eval_id = None
        status_label = "Updated"

        # 1. Check if this evaluation is outdated based on Learnify date
        rag_date = RagService.get_last_modified(module.course_key)
        if rag_date:
            last_modify = rag_date.date().isoformat()
            
            if last_eval:
                last_eval_id = last_eval.id
                last_evaluation_date = last_eval.created_at.date().isoformat()
                
                # Outdated check
                if last_eval.module_last_modified:
                    learnify_ts = rag_date.replace(second=0, microsecond=0)
                    stored_ts = last_eval.module_last_modified.replace(second=0, microsecond=0)
                    if learnify_ts > stored_ts:
                        status_label = "Outdated"
                
                # Self assessment check (overrides updated/outdated label)
                if last_eval.status == Evaluation.Status.SELF_ASSESSMENT:
                    status_label = "Self assessment"
                
                # Calculate average
                if last_eval.result_json:
                    total, count = EvaluationService.calculate_score_from_json(last_eval.result_json)
                    if count > 0:
                        last_avg = round(total / count, 2)

        response_data.append({
            "title": module.title,
            "link": module.course_key,
            "last_modify": last_modify,
            "last_evaluation": last_evaluation_date,
            "last_average": last_avg,
            "last_max": 5.0,
            "last_evaluation_id": last_eval_id,
            "status": status_label
        })

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_evaluation_pdf(request, pk):
    # Generates and returns a PDF report for a specific evaluation.
   
    evaluation = get_object_or_404(Evaluation, pk=pk)
    
    # 1. Access Control (Matches get_module_link logic)
    has_access = (evaluation.triggered_by == request.user) or \
                 UserModule.objects.filter(user=request.user, module=evaluation.module).exists()

    if not has_access:
        return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

    if not evaluation.result_json:
        return Response(
            {"error": "Evaluation incomplete or missing results. Cannot generate PDF."}, 
            status=status.HTTP_404_NOT_FOUND
        )

    # 2. Ensure Metadata exists (Critical for PDF header)
    if not evaluation.metadata_json:
        logger.info(f"Metadata missing for PDF (Eval {pk}). Fetching...")
        try:
            EvaluationService.fetch_and_update_metadata(evaluation)
            evaluation.refresh_from_db()
        except Exception as e:
            logger.error(f"Failed to fetch metadata during PDF generation: {e}")

    # Paths
    tmp_json_path = ""
    tmp_meta_path = ""
    tmp_pdf_path = ""

    try:
        # 3. Create a temporary JSON file for Results
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False, encoding='utf-8') as tmp_json:
            json.dump(evaluation.result_json, tmp_json)
            tmp_json_path = tmp_json.name
        
        # 4. Create a temporary JSON file for Metadata
        meta_content = evaluation.metadata_json if evaluation.metadata_json else {}
        with tempfile.NamedTemporaryFile(mode='w+', suffix='_meta.json', delete=False, encoding='utf-8') as tmp_meta:
            json.dump(meta_content, tmp_meta)
            tmp_meta_path = tmp_meta.name

        tmp_pdf_path = f"{tmp_json_path}.pdf"

        # 5. Generate PDF passing BOTH paths
        report_manager = ReportManager(tmp_json_path, tmp_meta_path)
        report_manager.generate_pdf_report(tmp_pdf_path)
        
        # 6. Read and Return
        if not os.path.exists(tmp_pdf_path):
             raise FileNotFoundError("PDF generator did not create the file.")

        with open(tmp_pdf_path, 'rb') as f:
            pdf_data = f.read()

        filename = f"Evaluation_{evaluation.module.course_key}_{pk}.pdf"
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        logger.error(f"Error generating PDF for evaluation {pk}: {e}")
        return Response({"error": "Failed to generate PDF on server."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        # 7. Cleanup
        if tmp_json_path and os.path.exists(tmp_json_path):
            os.remove(tmp_json_path)
        if tmp_meta_path and os.path.exists(tmp_meta_path):
            os.remove(tmp_meta_path)
        if tmp_pdf_path and os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_criterion_ai_suggestion(request, criterion_id):
    # AI suggestion for criterion
    criterion = get_object_or_404(Criterion, pk=criterion_id)
    scan = criterion.scan
    
    question = request.data.get("question") or request.data.get("review_question")
    description = request.data.get("description") or request.data.get("criteria_description")

    if not question or not description:
        return Response({"error": "Missing question or description"}, status=status.HTTP_400_BAD_REQUEST)

    payload = {
        "evaluation_id": scan.evaluation.id,
        "course_key": scan.evaluation.module.course_key,
        "review_question": question,
        "criteria_description": description,
        "criterion_name": criterion.criterion_name,
        "callback_url": f"{settings.SERVER_PUBLIC_URL.rstrip('/')}{reverse('evaluation_callback')}",
        "qip_user_id": str(request.user.id)
    }
    data, code = RagService.trigger_single_suggestion(payload)
    return Response(data, status=code)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_module_metadata(request):
    # Get and evaluate metadata from module
    course_key = request.data.get('moduleLink') or request.data.get('course_link')
    if not course_key:
        return Response({"error": "moduleLink required"}, status=status.HTTP_400_BAD_REQUEST)
    data, code = RagService.validate_metadata({"course_key": course_key})
    return Response(data, status=code)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_evaluation(request):
    # Initialize evaluation, create whole structure
    course_link = request.data.get('course_link')    
    if not course_link:
        return Response({"error": "course_link is required"}, status=status.HTTP_400_BAD_REQUEST)

    module = EvaluationService.ensure_module_access(request.user, course_link)
    try:
        evaluation, created = EvaluationService.get_or_create_evaluation_structure(module, request.user)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    resp_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK

    return Response({
        "message": "Evaluation started.",
        "evaluation_id": str(evaluation.id)
    }, status=resp_status)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_scans(request, module_id=None):
    # Get scans names, with scan ids if module id included
    if module_id:
        evaluation = get_object_or_404(Evaluation, pk=module_id)
        data = [
            {"id": str(scan.id), "name": scan.scan_type} 
            for scan in evaluation.scans.all()
        ]
        return Response(data, status=status.HTTP_200_OK)
    else:
        rubric = Rubric.objects.first()
        if not rubric:
            return Response([], status=status.HTTP_200_OK)
            
        data = [{"name": scan_name} for scan_name in rubric.available_scans]
        return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_scan_criterions(request, scan_id):
    # Returns the list of criteria for a specific scan
    scan = get_object_or_404(Scan, pk=scan_id)
    criterions = scan.criteria_results.all()
    serializer = CriterionListSerializer(criterions, many=True)
    
    return Response({"criterions": serializer.data}, status=status.HTTP_200_OK)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_criterion_selection(request, criterion_id):
    # Updates user selection (YES, NO, NOT APPLICABLE)
    criterion = get_object_or_404(Criterion, pk=criterion_id)
    
    serializer = CriterionUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Normalize input to match database choices
    selection = serializer.validated_data['result'].upper()
    if "APPLICABLE" in selection:
        selection = "NOT APPLICABLE"
        
    criterion.user_selection = selection
    criterion.save()
    
    return Response({
        "message": "Selection updated", 
        "id": criterion.id, 
        "selection": criterion.user_selection
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_criterion_result(request, criterion_id):
    criterion = get_object_or_404(Criterion, pk=criterion_id)
    return Response({"result": criterion.result}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_evaluation_basic_info(request, evaluation_id):
    # Get basic info from Learnify module
    evaluation = get_object_or_404(Evaluation, pk=evaluation_id)
    # 1. Check for metadata or ask to rag
    if not evaluation.metadata_json:
        logger.info(f"Metadata missing for Basic Info (Eval {evaluation_id}). Fetching...")
        try:
            EvaluationService.fetch_and_update_metadata(evaluation)
            evaluation.refresh_from_db()
        except Exception as e:
            logger.error(f"Failed to fetch metadata: {e}")

    # 2. Prepare data
    meta = evaluation.metadata_json or {}
    raw_keywords = meta.get('keywords', [])
    final_keywords = []
    
    if isinstance(raw_keywords, str):
        final_keywords = [k.strip() for k in raw_keywords.split(',') if k.strip()]
    elif isinstance(raw_keywords, list):
        final_keywords = raw_keywords

    # 3. Create response
    response_data = {
        "elh": meta.get('elh', "N/A"),
        "eqf": meta.get('eqf', "N/A"),
        "smcts": meta.get('smcts', "N/A"),
        "title": meta.get('title') or evaluation.title or evaluation.module.title or "Untitled Module",
        "abstract": meta.get('abstract', "No abstract available."),
        "keywords": final_keywords,
        "teachers": meta.get('teachers', "No teachers information available.")
    }

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['POST'])
@verify_rag_callback
@transaction.atomic
def evaluation_callback(request):
    # Handles RAG Webhooks.
    data = request.data
    status_cb = data.get('status')
    result = data.get('result')

    try:
        evaluation = Evaluation.objects.select_for_update().get(id=int(data.get('evaluation_id')))
    except (ValueError, TypeError, Evaluation.DoesNotExist):
        return Response({"message": "Invalid ID"}, status=status.HTTP_200_OK)

    # CASE 1: AI Suggestion (Allowed in any status)
    if status_cb in ['SUGGESTION_READY', 'SUGGESTION_FAILED']:
        crit_name = data.get('criterion_name')
        
        criterion = Criterion.objects.filter(
            scan__evaluation=evaluation, 
            criterion_name=crit_name
        ).first()

        if not criterion:
            return Response({"message": "Criterion not found in this evaluation"}, status=status.HTTP_404_NOT_FOUND)

        if status_cb == 'SUGGESTION_READY':
            # Save the suggestion text into the 'result' field
            criterion.result = data.get('suggestion', '')
            criterion.save()
            return Response({"message": "Suggestion saved"}, status=status.HTTP_200_OK)

        elif status_cb == 'SUGGESTION_FAILED':
            criterion.result = f"Error: {data.get('error', 'Unknown error')}"
            criterion.save()
            return Response({"message": "Suggestion failure recorded"}, status=status.HTTP_200_OK)

    # CASE 2: Standard Evaluation Lifecycle
    if evaluation.status in [Evaluation.Status.COMPLETED]:
        return Response({"message": "Already finished"}, status=status.HTTP_200_OK)

    # Scenario A: Snapshot
    if status_cb == 'SNAPSHOT_CREATED':
        if result and isinstance(result, str):
            evaluation.document_snapshot = result
            evaluation.save()
        return Response({"message": "Snapshot saved"}, status=status.HTTP_200_OK)

    # Scenario B: Interim Progress
    elif status_cb == 'CRITERION_COMPLETE':
        if not result or 'content' not in result: 
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        scan_data = result['content'][0]
        s_name = scan_data.get('scan')
        valid_types = EvaluationService.get_valid_scan_types(evaluation.rubric)
        
        if s_name in valid_types:
            Scan.objects.update_or_create(
                evaluation=evaluation, scan_type=s_name,
                defaults={
                    'status': Scan.Status.IN_PROGRESS,
                    'result_json': result
                }
            )
            EvaluationService.merge_scan_results(evaluation, [scan_data])

        return Response({"message": "Interim merged"}, status=status.HTTP_200_OK)

    # Scenario C: Evaluation Finished
    elif status_cb == 'COMPLETE':
        if not result: return Response(status=status.HTTP_400_BAD_REQUEST)
        
        EvaluationService.handle_evaluation_completion(evaluation, result)
        return Response({"message": "Completed processed"}, status=status.HTTP_200_OK)

    # Scenario D: Failure (Granular & CLEANUP)
    elif status_cb == 'FAILED':
        failed_scans = data.get('scan_names', [])
        
        if failed_scans:
            Scan.objects.filter(evaluation=evaluation, scan_type__in=failed_scans).update(status=Scan.Status.FAILED)
        else:
            Scan.objects.filter(evaluation=evaluation, status=Scan.Status.IN_PROGRESS).update(status=Scan.Status.FAILED)

        failed_scan_types = set(Scan.objects.filter(evaluation=evaluation, status=Scan.Status.FAILED).values_list('scan_type', flat=True))
        
        if evaluation.result_json and 'content' in evaluation.result_json:
            current_content = evaluation.result_json.get('content', [])
            clean_content = [item for item in current_content if item.get('scan') not in failed_scan_types]
            evaluation.result_json['content'] = clean_content

        evaluation.error_message = data.get('error', "Unknown error")
        evaluation.save()
        EvaluationService.check_and_update_status(evaluation)
        return Response({"message": "Failure processed (Partial)"}, status=status.HTTP_200_OK)

    return Response(status=status.HTTP_400_BAD_REQUEST)
