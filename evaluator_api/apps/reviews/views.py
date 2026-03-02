from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction

from apps.evaluations.models import Evaluation, Criterion
from .models import ExternalReview
from .serializers import *
from .services import ReviewService
from .security import verify_review_token

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def request_peer_reviews(request):
    # Invite multiple external reviewers to an evaluation
    serializer = RequestPeerReviewsSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    emails = serializer.validated_data['emails']
    evaluation_id = serializer.validated_data['evaluationId']
    evaluation = get_object_or_404(Evaluation, pk=evaluation_id)
    
    # Process each email in the list
    for email in emails:
        review, created = ExternalReview.objects.get_or_create(
            evaluation=evaluation,
            reviewer_email=email
        )
        
        if not review.is_completed:
            try:
                ReviewService.send_invitation_email(review)
            except Exception:
                continue
    return Response({"email_sent": True}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_evaluation_reviews(request, evaluation_id):
    # Retrieve a list of all fully completed external reviews for a specific evaluation
    get_object_or_404(Evaluation, pk=evaluation_id)
    raw_data = ReviewService.get_completed_reviews_summary(evaluation_id)
    serializer = ReviewSummaryResponseSerializer(raw_data, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_review_scans_info(request, review_id):
    # Retrieve grouped score averages for a specific external review
    get_object_or_404(ExternalReview, pk=review_id)
    raw_data = ReviewService.get_review_scans_info(review_id)
    serializer = ReviewScanInfoSerializer(raw_data, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_review_details(request, review_id, scan_id):
    # Retrieve the detailed breakdown for a specific scan belonging to a specific review
    get_object_or_404(ExternalReview, pk=review_id)
    raw_data = ReviewService.get_review_details(review_id, scan_id)
    serializer = ReviewDetailResponseSerializer(raw_data)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny]) # No JWT
@verify_review_token            # Protected by Token
def get_external_review_details(request, review_session):
    # Public endpoint to validate a token and return basic review mapping IDs
    raw_data = ReviewService.get_review_token_details(review_session)
    serializer = ReviewTokenDetailsResponseSerializer(raw_data) 
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PUT'])
@permission_classes([AllowAny]) # No JWT
@verify_review_token            # Protected by Token
def update_criterion_feedback(request, review_session, criterion_id):
    # Updates or creates the feedback for a single criterion using the magic token
    criterion = get_object_or_404(
        Criterion, 
        pk=criterion_id, 
        scan__evaluation=review_session.evaluation
    )
    serializer = UpdateCriterionFeedbackSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 
    score = serializer.validated_data['value']
    comment = serializer.validated_data.get('note', '')
    ReviewService.save_criterion_feedback(review_session, criterion, score, comment)
    return Response({"message": "Feedback saved successfully"}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny]) # No JWT
@verify_review_token            # Protected by Token
def submit_review(request, review_session):
    # Finalizes the review process, locking it from future edits
    ReviewService.submit_review(review_session)
    return Response(
        {"message": "Evaluation successfully submitted and completed."}, 
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([AllowAny]) # No JWT
@verify_review_token            # Protected by Token
def get_review_completion_status(request, review_session):
    # Returns true/false for each scan based on external reviewer's progress
    result = ReviewService.get_completion_status(review_session)
    return Response(result, status=status.HTTP_200_OK)
