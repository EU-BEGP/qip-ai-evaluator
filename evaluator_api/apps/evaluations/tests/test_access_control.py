# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.evaluations.models import Scan
from apps.evaluations.services.rag_service import RagService
from apps.evaluations.tests.conftest import COURSE_LINK, ensure_rubric, make_evaluation, make_user


class EvaluationAccessControlTest(TestCase):
    """Object-level authorization: a user may only read evaluations of modules they follow."""

    def setUp(self):
        ensure_rubric()
        self.owner = make_user(email="owner@test.com")
        self.other = make_user(email="other@test.com")

        # Avoid hitting Celery / RAG during creation and request handling.
        patch("apps.evaluations.tasks.async_sync_module_metadata.delay").start()
        patch.object(RagService, "get_last_modified", return_value="2026-01-01T00:00:00Z").start()
        self.addCleanup(patch.stopall)

        _, self.evaluation = make_evaluation(self.owner)
        self.scan = Scan.objects.filter(evaluation=self.evaluation).first()

    def _client(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def _object_endpoints(self):
        return [
            reverse("evaluation_status_module", args=[self.evaluation.id]),
            reverse("evaluation_status_scan", args=[self.scan.id]),
            reverse("evaluation_detail_module", args=[self.evaluation.id]),
            reverse("evaluation_detail_scan", args=[self.scan.id]),
            reverse("get_evaluation_ids", args=[self.evaluation.id]),
            reverse("get_evaluation_basic_info", args=[self.evaluation.id]),
        ]

    def test_owner_can_read_own_evaluation(self):
        client = self._client(self.owner)
        for url in self._object_endpoints():
            self.assertEqual(client.get(url).status_code, 200, msg=url)

    def test_other_user_gets_404_on_foreign_evaluation(self):
        client = self._client(self.other)
        for url in self._object_endpoints():
            self.assertEqual(client.get(url).status_code, 404, msg=url)

    def test_link_module_denies_foreign_user(self):
        owner_resp = self._client(self.owner).get(reverse("get_module_link", args=[self.evaluation.id]))
        other_resp = self._client(self.other).get(reverse("get_module_link", args=[self.evaluation.id]))

        self.assertEqual(owner_resp.status_code, 200)
        self.assertEqual(other_resp.status_code, 403)

    def test_history_is_scoped_to_follower(self):
        url = reverse("list_evaluations")
        owner_resp = self._client(self.owner).post(url, {"course_link": COURSE_LINK}, format="json")
        other_resp = self._client(self.other).post(url, {"course_link": COURSE_LINK}, format="json")

        self.assertEqual(owner_resp.status_code, 200)
        self.assertEqual(len(owner_resp.data), 1)
        self.assertEqual(other_resp.status_code, 200)
        self.assertEqual(len(other_resp.data), 0)
