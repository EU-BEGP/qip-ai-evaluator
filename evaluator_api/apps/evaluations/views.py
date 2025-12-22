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

from .models import Module, Evaluation, Scan, UserModule
from apps.notifications.models import Message
from .serializers import StartEvaluationSerializer, EvaluationDetailSerializer
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
    module = EvaluationService.ensure_module_access(user, data['course_link'])
    
    rag_date_str = RagService.get_last_modified(module.course_key)
    if not rag_date_str:
        return Response({"error": "Verify module failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    rag_date = isoparse(rag_date_str)
    if rag_date.tzinfo is None:
        rag_date = rag_date.replace(tzinfo=datetime.timezone.utc)

    try:
        evaluation, _ = EvaluationService.resolve_evaluation_instance(
            module, user, rag_date, data.get('evaluation_id'), data.get('scan_name')
        )
    except (ValueError, LookupError) as e:
        status_code = status.HTTP_409_CONFLICT if isinstance(e, ValueError) else status.HTTP_404_NOT_FOUND
        return Response({"error": str(e)}, status=status_code)

    scans_to_run, created_objs, is_all = EvaluationService.prepare_scans_and_placeholders(
        evaluation, data.get('scan_name'), user
    )

    if not scans_to_run:
        ret_id = evaluation.id
        if not is_all and data.get('scan_name'):
            try: ret_id = evaluation.scans.get(scan_type=data.get('scan_name')).id
            except Scan.DoesNotExist: pass
        return Response({"message": "Cached.", "evaluation_id": evaluation.id, "scan_id": ret_id})

    payload = {
        "evaluation_id": evaluation.id,
        "course_key": module.course_key,
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
        Scan.objects.filter(evaluation=evaluation, scan_type__in=scans_to_run).update(status=Scan.Status.FAILED)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    resp_scan_id = created_objs[0].id if (not is_all and created_objs) else evaluation.id
    return Response({"message": "Started.", "evaluation_id": evaluation.id, "scan_id": resp_scan_id}, status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_evaluation_ids(request, pk):
    # Returns status/evaluability of all scans; checks for outdated content [cite: 11]
    evaluation = get_object_or_404(Evaluation, pk=pk)
    
    rag_date_str = RagService.get_last_modified(evaluation.module.course_key)
    is_outdated = False
    if rag_date_str:
        try:
            rag_date = isoparse(rag_date_str)
            if rag_date.tzinfo is None: rag_date = rag_date.replace(tzinfo=datetime.timezone.utc)
            if rag_date.replace(second=0, microsecond=0) > evaluation.created_at.replace(second=0, microsecond=0):
                is_outdated = True
        except Exception: pass

    active_scans = set(evaluation.scans.filter(status__in=[Scan.Status.IN_PROGRESS, Scan.Status.COMPLETED]).values_list('scan_type', flat=True))
    missing_scans = set(Scan.ScanType.values) - active_scans
    
    existing_scans_map = {s.scan_type: s for s in evaluation.scans.all()}
    response_list, global_total, global_count = [], 0.0, 0
    scans_data = []

    for s_type in Scan.ScanType.values:
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
        scans_data.append({"name": s_type, "id": s_id, "evaluable": s_evaluable, "scan_max": 5.0, "scan_average": s_avg, "status": s_status})

    global_avg = round(global_total/global_count, 2) if global_count > 0 else None
    response_list.append({
        "name": "All Scans", "id": evaluation.id, "evaluable": (len(missing_scans) > 0 and not is_outdated),
        "scan_max": 5.0, "scan_average": global_avg, "status": evaluation.status
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
    if evaluation.status not in [Evaluation.Status.IN_PROGRESS, Evaluation.Status.COMPLETED]:
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

    evals = Evaluation.objects.filter(module=module).order_by('-updated_at')[:20]
    if not evals.exists(): return Response(status=status.HTTP_404_NOT_FOUND)

    data = [{
        "id": e.id, 
        "date": e.updated_at.strftime("%Y-%m-%d %H:%M"), 
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
    # Dashboard: returns modules and stats for user
    if request.user.email != email: return Response(status=status.HTTP_403_FORBIDDEN)
    
    modules = EvaluationService.get_user_dashboard_modules(request.user)
    response_list = []
    
    for mod in modules:
        eval_obj = mod.evaluations.exclude(status=Evaluation.Status.NOT_STARTED).order_by('-updated_at').first()
        rag_date = RagService.get_last_modified(mod.course_key)
        
        last_date, last_avg = "N/A", 0.0
        title = eval_obj.title if (eval_obj and eval_obj.title) else (mod.title or "Pending...")

        if eval_obj:
            last_date = eval_obj.updated_at.strftime("%Y-%m-%d")
            s, c = EvaluationService.calculate_score_from_json(eval_obj.result_json)
            if c == 0: 
                for sc in eval_obj.scans.all():
                    sub_s, sub_c = EvaluationService.calculate_score_from_json(sc.result_json)
                    s += sub_s; c += sub_c
            if c > 0: last_avg = round(s/c, 2)

        fmt_rag = "N/A"
        if rag_date:
            try: fmt_rag = isoparse(rag_date).strftime("%Y-%m-%d")
            except: pass
            
        response_list.append({
            "title": title, "link": mod.course_key, "last_modify": fmt_rag,
            "last_evaluation": last_date, "last_average": last_avg, "last_max": 5.0
        })
    return Response(response_list)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_evaluation_pdf(request, pk):
    # Generates and downloads PDF report
    evaluation = get_object_or_404(Evaluation, pk=pk)
    if not evaluation.result_json: return Response(status=status.HTTP_404_NOT_FOUND)
    try:
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as t_json:
            json.dump(evaluation.result_json, t_json)
            t_json_path = t_json.name
        
        t_pdf = f"{t_json_path}.pdf"
        ReportManager(t_json_path, None).generate_pdf_report(t_pdf)
        
        with open(t_pdf, 'rb') as f: data = f.read()
        response = HttpResponse(data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Evaluation_{pk}.pdf"'
        return response
    except Exception as e:
        logger.error(f"PDF Error: {e}")
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        if os.path.exists(t_json_path): os.remove(t_json_path)
        if 't_pdf' in locals() and os.path.exists(t_pdf): os.remove(t_pdf)

@api_view(['POST'])
@verify_rag_callback
@transaction.atomic
def evaluation_callback(request):
    # Handles RAG Webhooks.
    data = request.data
    try:
        evaluation = Evaluation.objects.select_for_update().get(id=int(data.get('evaluation_id')))
    except (ValueError, TypeError, Evaluation.DoesNotExist):
        return Response({"message": "Invalid ID"}, status=status.HTTP_200_OK)

    if evaluation.status in [Evaluation.Status.COMPLETED, Evaluation.Status.FAILED]:
        return Response({"message": "Already finished"}, status=status.HTTP_200_OK)

    status_cb, result = data.get('status'), data.get('result')

    # Scenario A: Snapshot
    if status_cb == 'SNAPSHOT_CREATED':
        if result and isinstance(result, str):
            evaluation.document_snapshot = result
            evaluation.save()
        return Response({"message": "Snapshot saved"}, status=status.HTTP_200_OK)

    # Scenario B: Interim Progress
    elif status_cb == 'CRITERION_COMPLETE':
        if not result or 'content' not in result: return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            partial = result['content'][0]; scan_name = partial.get('scan')
        except: return Response(status=status.HTTP_400_BAD_REQUEST)
        
        Scan.objects.update_or_create(
            evaluation=evaluation, scan_type=scan_name,
            defaults={'status': Scan.Status.IN_PROGRESS, 'result_json': result}
        )

        curr_json = evaluation.result_json or {"title": result.get("title", ""), "content": []}
        curr_content = curr_json.get("content", [])
        idx = next((i for i, item in enumerate(curr_content) if item.get('scan') == scan_name), -1)
        
        if idx >= 0: curr_content[idx] = partial
        else: curr_content.append(partial)
        
        if result.get('title'): curr_json['title'] = result['title']
        curr_json['content'] = curr_content
        evaluation.result_json = curr_json
        evaluation.save()
        return Response({"message": "Interim merged"}, status=status.HTTP_200_OK)

    # Scenario C: Evaluation Finished
    elif status_cb == 'COMPLETE':
        if not result: return Response(status=status.HTTP_400_BAD_REQUEST)
        
        if result.get('title'):
            evaluation.title = result['title']
            if evaluation.module:
                evaluation.module.title = result['title']
                evaluation.module.save()

        for scan_data in result.get('content', []):
            s_name = scan_data.get('scan')
            Scan.objects.update_or_create(
                evaluation=evaluation, scan_type=s_name,
                defaults={
                    'status': Scan.Status.COMPLETED, 
                    'result_json': {"title": evaluation.title, "content": [scan_data]}
                }
            )

            if evaluation.triggered_by:
                Message.objects.get_or_create(
                    user=evaluation.triggered_by, 
                    evaluation=evaluation, 
                    scan_type=s_name,
                    defaults={
                        "title": f"{s_name} Finished: {evaluation.module.course_key}", 
                        "content": f"The {s_name} has finished successfully for {evaluation.title}.", 
                        "is_read": False
                    }
                )

        current_json = evaluation.result_json or {"title": evaluation.title, "content": []}
        current_content = current_json.get("content", [])
        content_map = {item.get('scan'): item for item in current_content}

        new_content_list = result.get('content', [])
        for new_item in new_content_list:
            scan_type = new_item.get('scan')
            content_map[scan_type] = new_item 

        merged_content = list(content_map.values())
        evaluation.result_json = {
            "title": evaluation.title,
            "content": merged_content
        }

        completed_types = set(evaluation.scans.filter(status=Scan.Status.COMPLETED).values_list('scan_type', flat=True))
        evaluation.status = Evaluation.Status.COMPLETED if set(Scan.ScanType.values).issubset(completed_types) else Evaluation.Status.IN_PROGRESS
        evaluation.save()
        return Response({"message": "Completed processed and merged"}, status=status.HTTP_200_OK)

    # Scenario D: Failure
    elif status_cb == 'FAILED':
        evaluation.status = Evaluation.Status.FAILED
        evaluation.error_message = data.get('error', "Unknown error")
        evaluation.save()
        evaluation.scans.update(status=Scan.Status.FAILED)
        return Response({"message": "Failure processed"}, status=status.HTTP_200_OK)

    return Response(status=status.HTTP_400_BAD_REQUEST)
