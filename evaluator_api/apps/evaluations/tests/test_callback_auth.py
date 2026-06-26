# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class RagCallbackAuthTest(TestCase):
    """The RAG webhook endpoint must reject any caller without the shared secret."""

    def setUp(self):
        self.url = reverse("evaluation_callback")
        self.client = APIClient()

    def test_missing_secret_is_forbidden(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_wrong_secret_is_forbidden(self):
        resp = self.client.post(self.url, {}, format="json", HTTP_X_CALLBACK_SECRET="wrong-secret")
        self.assertEqual(resp.status_code, 403)

    def test_correct_secret_passes_auth(self):
        resp = self.client.post(
            self.url, {}, format="json", HTTP_X_CALLBACK_SECRET=settings.RAG_CALLBACK_SECRET
        )
        self.assertNotEqual(resp.status_code, 403)
        self.assertEqual(resp.status_code, 400)
