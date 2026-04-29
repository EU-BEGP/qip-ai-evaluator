# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from unittest.mock import patch

from django.test import TestCase

from apps.evaluations.services.webhooks_service import WebhookHandlerService
from apps.evaluations.tests.conftest import ensure_rubric, make_evaluation, make_user
from apps.notifications.models import Message

SCAN_TYPE = "Academic Metadata Scan"


def _complete_payload(scan_type=SCAN_TYPE):
    return {
        "status": "COMPLETE",
        "result": {
            "title": "Test Module",
            "content": [{"scan": scan_type, "criteria": []}],
        },
    }


class NotificationTest(TestCase):
    def setUp(self):
        ensure_rubric()
        patch("apps.evaluations.tasks.async_sync_module_metadata.delay").start()
        self.addCleanup(patch.stopall)
        self.user = make_user()
        self.module, self.evaluation = make_evaluation(self.user)

    def test_complete_webhook_creates_message(self):
        WebhookHandlerService.process_callback(self.evaluation, _complete_payload())

        msg = Message.objects.filter(
            user=self.user,
            evaluation=self.evaluation,
            scan_type=SCAN_TYPE,
        ).first()

        self.assertIsNotNone(msg)
        self.assertFalse(msg.is_read)
        self.assertIn(SCAN_TYPE, msg.title)
        self.assertIn(SCAN_TYPE, msg.content)

    def test_complete_webhook_idempotent(self):
        WebhookHandlerService.process_callback(self.evaluation, _complete_payload())
        WebhookHandlerService.process_callback(self.evaluation, _complete_payload())

        count = Message.objects.filter(
            user=self.user,
            evaluation=self.evaluation,
            scan_type=SCAN_TYPE,
        ).count()

        self.assertEqual(count, 1)

    def test_no_message_when_no_triggered_by(self):
        self.evaluation.triggered_by = None
        self.evaluation.save(update_fields=["triggered_by"])

        WebhookHandlerService.process_callback(self.evaluation, _complete_payload())

        self.assertEqual(
            Message.objects.filter(evaluation=self.evaluation).count(), 0
        )
