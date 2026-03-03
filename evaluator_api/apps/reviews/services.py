import logging
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Avg
from django.utils import timezone
from .models import ExternalReview 
from apps.evaluations.services import EvaluationService
from apps.evaluations.models import UserModule
from apps.notifications.models import Message

logger = logging.getLogger(__name__)

class ReviewService:    
    @staticmethod
    def send_invitation_email(external_review):
        # Generates the access link and sends the email to the reviewer
        client_url = getattr(settings, 'CLIENT_PUBLIC_URL', 'http://localhost:4200')
        
        # 1. Construct the link using the UUID token
        access_link = f"{client_url}/external-review/{external_review.token}"
        module = external_review.evaluation.module
        module_title = module.title or "Untitled Module"
        course_link = module.course_key
        evaluation_id = external_review.evaluation.id
        
        # 2. Build the subject and message body
        subject = f"QIP evaluator: Invitation to Review Module '{module_title}'"
        message = (
            f"Hello,\n\n"
            f"You have been invited to participate as an external reviewer in the QIP evaluator.\n\n"
            f"Evaluation Details:\n"
            f"- Module Title: {module_title}\n"
            f"- Evaluation ID: {evaluation_id}\n"
            f"- Course Link: {course_link}\n\n"
            f"Please submit your review by accessing your unique, secure link below:\n"
            f"{access_link}\n\n"
            f"Note: This access link is securely generated and unique to you. Please do not share it with others.\n\n"
            f"Best regards,\n"
            f"The QIP evaluator Team"
        )
        
        try:
            # 3. Send the email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[external_review.reviewer_email],
                fail_silently=False,
            )
            
            logger.info(f"Invitation email successfully sent to {external_review.reviewer_email}")
            return access_link
            
        except Exception as e:
            logger.error(f"Failed to send review invitation email to {external_review.reviewer_email}: {e}")
            raise e
        
    @staticmethod
    def get_completed_reviews_summary(evaluation_id):
        # Ge completed reviews
        completed_reviews = ExternalReview.objects.filter(
            evaluation_id=evaluation_id,
            is_completed=True
        ).prefetch_related('feedbacks')
        
        results = []
        
        for review in completed_reviews:
            # Calculate the average score of all feedbacks given by this reviewer
            avg_score_dict = review.feedbacks.aggregate(Avg('score'))
            avg_score = avg_score_dict['score__avg']
            final_score = round(avg_score, 1) if avg_score is not None else 0.0
            date_obj = review.completed_at or review.created_at
            local_date = timezone.localtime(date_obj)
            formatted_date = local_date.strftime("%Y-%m-%d %H:%M")
            
            results.append({
                "id": review.id,
                "reviewer": review.reviewer_email,
                "review_max": 5.0,
                "review_score": final_score,
                "date": formatted_date
            })
                
        return results
    
    @staticmethod
    def _is_evaluation_outdated(evaluation):
        # Checks if the evaluation is outdated compared to the current module version
        from apps.evaluations.models import Evaluation
        from apps.evaluations.services import RagService

        module = evaluation.module
        latest_local = Evaluation.objects.filter(module=module).order_by('-created_at').first()
        
        # Check if there's a newer evaluation in the database
        if latest_local and latest_local.id != evaluation.id:
            return True
            
        # Check if the module was modified in the Learnify system after this evaluation was evaluated
        rag_date = RagService.get_last_modified(module.course_key)
        if rag_date and rag_date.replace(second=0, microsecond=0) > evaluation.created_at.replace(second=0, microsecond=0):
            return True
            
        return False
    
    @staticmethod
    def _calculate_scan_averages(review, expected_scans_list, scan_id_map):
        # Groups feedback scores by scan type and calculates the averages
        scan_scores = {}
        global_total = 0.0
        global_count = 0

        # Group all scores by their scan
        for feedback in review.feedbacks.all():
            scan_type = feedback.criterion.scan.scan_type
            score_val = float(feedback.score) if feedback.score is not None else 0.0
            
            if scan_type not in scan_scores:
                scan_scores[scan_type] = {'total': 0.0, 'count': 0}

            scan_scores[scan_type]['total'] += score_val
            scan_scores[scan_type]['count'] += 1
            global_total += score_val
            global_count += 1

        scans_data = []
        
        for s_type in expected_scans_list:
            s_avg = None
            if s_type in scan_scores and scan_scores[s_type]['count'] > 0:
                s_avg = round(scan_scores[s_type]['total'] / scan_scores[s_type]['count'], 2)
            
            scans_data.append({
                "name": s_type,
                "id": scan_id_map.get(s_type),
                "scan_average": s_avg
            })

        global_avg = round(global_total / global_count, 2) if global_count > 0 else None
        return global_avg, scans_data
    
    @staticmethod
    def get_review_scans_info(review_id):
        # Orchestrates the retrieval and formatting of scan info for a specific review
        review = ExternalReview.objects.select_related(
            'evaluation__module', 'evaluation__rubric'
        ).prefetch_related(
            'feedbacks__criterion__scan', 
            'evaluation__scans'
        ).get(pk=review_id)
        
        evaluation = review.evaluation
        is_outdated = ReviewService._is_evaluation_outdated(evaluation)
        expected_scans_list = EvaluationService.get_valid_scan_types(evaluation.rubric)
        
        # 1. Create a dictionary mapping scan names to their actual IDs
        scan_id_map = {scan.scan_type: scan.id for scan in evaluation.scans.all()}
        global_avg, specific_scans_data = ReviewService._calculate_scan_averages(review, expected_scans_list, scan_id_map)
        review_status = "Completed" if review.is_completed else "Incompleted"
        
        # 2. Build response payload (All Scans uses evaluation.id)
        results = [{
            "name": "All Scans",
            "id": evaluation.id,
            "scan_max": 5.0,
            "scan_average": global_avg,
            "status": review_status,
            "outdated": is_outdated
        }]

        # 3. Individual scans use their respective scan.id
        for scan_data in specific_scans_data:
            results.append({
                "name": scan_data["name"],
                "id": scan_data["id"],
                "scan_max": 5.0,
                "scan_average": scan_data["scan_average"],
                "status": review_status,
                "outdated": is_outdated
            })

        return results
    
    @staticmethod
    def get_review_details(review_id, scan_id):
        # Fetches and formats feedback for a specific review and a specific scan
        from apps.evaluations.models import Scan
        from django.shortcuts import get_object_or_404
        
        review = ExternalReview.objects.select_related(
            'evaluation__module', 'evaluation__rubric'
        ).get(pk=review_id)
        
        scan = get_object_or_404(Scan, pk=scan_id)
        evaluation = review.evaluation
        module_title = evaluation.module.title or "Untitled Module"
        scan_name = scan.scan_type
        
        # 1. Extract descriptions for this Scan and its Criteria from the rubric
        scan_desc = ""
        crit_info = {}
        
        if evaluation.rubric and evaluation.rubric.content:
            content = evaluation.rubric.content
            if isinstance(content, list):
                for s in content:
                    if isinstance(s, dict) and s.get('scan') == scan_name:
                        scan_desc = s.get('description', '')
                        for c in s.get('criteria', []):
                            if 'name' in c:
                                crit_info[c['name']] = c.get('description', '')
                        break
            elif isinstance(content, dict):
                scans_dict = content.get('scans', {})
                if isinstance(scans_dict, dict) and scan_name in scans_dict:
                    scan_data = scans_dict[scan_name]
                    if isinstance(scan_data, dict):
                        scan_desc = scan_data.get('description', '')
                        for c in scan_data.get('criteria', []):
                            if 'name' in c:
                                crit_info[c['name']] = c.get('description', '')

        # 2. Get feedbacks associated with this specific review and scan
        feedbacks = review.feedbacks.filter(
            criterion__scan_id=scan_id
        ).select_related('criterion')
        criteria_list = []
        if feedbacks.exists():
            for feedback in feedbacks:
                criterion_name = feedback.criterion.criterion_name
                note_text = feedback.comment if feedback.comment else "NO NOTE"
                
                criteria_list.append({
                    "name": criterion_name,
                    "description": crit_info.get(criterion_name, ""), 
                    "score": float(feedback.score) if feedback.score is not None else 0.0,
                    "note": note_text,
                    "max_score": 5
                })
        else:
            for criterion in scan.criteria.all():
                criteria_list.append({
                    "name": criterion.criterion_name,
                    "description": crit_info.get(criterion.criterion_name, ""), 
                    "score": None,
                    "note": "NO NOTE",
                    "max_score": 5
                })
        scan_content = {
            "scan": scan_name,
            "description": scan_desc,
            "criteria": criteria_list
        }
        
        return {
            "title": module_title,
            "content": [scan_content]
        }
    
    @staticmethod
    def get_review_token_details(review_session):
        # Maps the review session object to the required basic details dictionary
        return {
            "evaluator_id": review_session.id,
            "evaluation_id": review_session.evaluation_id
        }

    @staticmethod
    def save_criterion_feedback(review_session, criterion, score, comment):
        # Updates or creates the feedback score for a specific criterion
        from .models import CriterionFeedback
        
        feedback, created = CriterionFeedback.objects.update_or_create(
            review=review_session,
            criterion=criterion,
            defaults={
                'score': score,
                'comment': comment
            }
        )
        return feedback

    @staticmethod
    def submit_review(review_session):
        # Locks the review session by marking it as completed and creates notifications for the module owners
        review_session.mark_as_completed()
        try:            
            evaluation = review_session.evaluation
            module = evaluation.module
            module_title = module.title or "Untitled Module"
            reviewer_email = review_session.reviewer_email
            # Get all users linked with the module
            user_modules = UserModule.objects.filter(module=module).select_related('user')
            # Prepare message
            messages_to_create = []
            for um in user_modules:
                messages_to_create.append(
                    Message(
                        user=um.user,
                        title="Peer Review Completed",
                        content=f"The external reviewer {reviewer_email} has submitted their feedback for the module '{module_title}'.",
                        evaluation=evaluation,
                        type='Peer Review',
                        reviewer_id=review_session.id
                    )
                )
            if messages_to_create:
                Message.objects.bulk_create(messages_to_create)
                logger.info(f"Notifications sent for module {module.id} after review {review_session.id}")
                
        except Exception as e:
            logger.error(f"Failed to create notifications for review {review_session.id}: {e}")

    @staticmethod
    def get_completion_status(review_session):
        # Checks if all criteria for each scan have been evaluated by the reviewer
        evaluation = review_session.evaluation
        scans = evaluation.scans.prefetch_related('criteria_results').all()
        from .models import CriterionFeedback
        evaluated_criteria_ids = set(
            CriterionFeedback.objects.filter(review=review_session).values_list('criterion_id', flat=True)
        )
        scan_complete_list = []
        for scan in scans:
            criteria = scan.criteria_results.all()
            if not criteria:
                # If there are no criteria, it cannot be marked as complete
                scan_complete_list.append({
                    "name": scan.scan_type, 
                    "isComplete": False
                })
            else:
                # It is complete only if ALL criteria IDs exist in the evaluated set
                is_complete = all(c.id in evaluated_criteria_ids for c in criteria)
                scan_complete_list.append({
                    "name": scan.scan_type, 
                    "isComplete": is_complete
                })
        return {"scanComplete": scan_complete_list}
