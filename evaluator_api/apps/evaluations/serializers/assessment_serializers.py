# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework import serializers


class ResultSerializer(serializers.Serializer):
    """Serializer for returning the result_json of an Evaluation or Scan."""

    result_json = serializers.JSONField()
