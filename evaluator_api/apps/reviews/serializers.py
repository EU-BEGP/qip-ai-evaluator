from rest_framework import serializers
from .models import ExternalReview, CriterionFeedback

class RequestPeerReviewsSerializer(serializers.Serializer):
    # Serializes the request to send multiple peer review invitations
    emails = serializers.ListField(
        child=serializers.EmailField(),
        allow_empty=False
    )
    evaluationId = serializers.IntegerField(required=True)

class ReviewSummaryResponseSerializer(serializers.Serializer):
    # Serializes the summary of a completed external review
    id = serializers.IntegerField()
    reviewer = serializers.EmailField()
    review_max = serializers.FloatField(default=5.0)
    review_score = serializers.FloatField()
    date = serializers.CharField()

class ReviewScanInfoSerializer(serializers.Serializer):
    # Serializes the grouped scan averages for a specific peer review
    name = serializers.CharField()
    id = serializers.IntegerField()
    scan_max = serializers.FloatField(default=5.0)
    scan_average = serializers.FloatField(allow_null=True)
    status = serializers.CharField()
    outdated = serializers.BooleanField()

class CriterionDetailSerializer(serializers.Serializer):
    # Serializes individual criterion feedback details
    name = serializers.CharField()
    description = serializers.CharField()
    score = serializers.FloatField(allow_null=True)
    note = serializers.CharField()
    max_score = serializers.IntegerField(default=5)

class ScanDetailSerializer(serializers.Serializer):
    # Serializes a scan and its list of evaluated criteria
    scan = serializers.CharField()
    description = serializers.CharField(allow_blank=True, allow_null=True)
    criteria = CriterionDetailSerializer(many=True)

class ReviewDetailResponseSerializer(serializers.Serializer):
    # Serializes the root response for the review detail endpoint
    title = serializers.CharField()
    content = ScanDetailSerializer(many=True)

class ReviewTokenDetailsResponseSerializer(serializers.Serializer):
    # Serializes the basic details extracted from a valid review token
    evaluator_id = serializers.IntegerField()
    evaluation_id = serializers.IntegerField()

class UpdateCriterionFeedbackSerializer(serializers.Serializer):
    # Serializes the request to update a single criterion score
    value = serializers.FloatField(required=True)
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_value(self, value):
        # Ensure score is between 0.0 and 5.0
        if not (0.0 <= value <= 5.0):
            raise serializers.ValidationError("Score must be between 0.0 and 5.0")
        # Ensure score is in steps of 0.5
        if (value * 10) % 5 != 0:
            raise serializers.ValidationError("Score must be in steps of 0.5")
        return value
