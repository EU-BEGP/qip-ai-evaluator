# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from unittest.mock import patch

from django.test import TestCase

from apps.evaluations.models import Evaluation, Module, Rubric, Scan, UserModule
from apps.evaluations.services.life_cycle_service import LifecycleService
from apps.evaluations.tests.conftest import COURSE_KEY, COURSE_LINK, ensure_rubric, make_evaluation, make_user


class EvaluationCreationTest(TestCase):
    """Golden path: ensure_module_access → get_or_create_evaluation_structure."""

    def setUp(self):
        self.rubric = ensure_rubric()
        self.user = make_user()
        patch("apps.evaluations.tasks.async_sync_module_metadata.delay").start()
        self.addCleanup(patch.stopall)

    def test_module_and_user_module_created(self):
        module, _ = make_evaluation(self.user)

        self.assertEqual(Module.objects.count(), 1)
        self.assertEqual(module.course_key, COURSE_KEY)
        self.assertEqual(module.course_link, COURSE_LINK)
        self.assertTrue(UserModule.objects.filter(user=self.user, module=module).exists())

    def test_evaluation_has_correct_status_and_links(self):
        module, evaluation = make_evaluation(self.user)

        self.assertEqual(evaluation.status, Evaluation.Status.NOT_STARTED)
        self.assertEqual(evaluation.module, module)
        self.assertEqual(evaluation.triggered_by, self.user)
        self.assertEqual(evaluation.rubric, self.rubric)

    def test_scans_created_for_every_rubric_scan(self):
        _, evaluation = make_evaluation(self.user)

        expected = set(self.rubric.available_scans)
        actual = set(Scan.objects.filter(evaluation=evaluation).values_list("scan_type", flat=True))

        self.assertEqual(actual, expected)
        self.assertFalse(
            Scan.objects.filter(evaluation=evaluation).exclude(status=Scan.Status.PENDING).exists()
        )

    def test_second_call_reuses_existing_not_started_evaluation(self):
        module, eval1 = make_evaluation(self.user)
        eval2, created = LifecycleService.get_or_create_evaluation_structure(module, self.user)

        self.assertFalse(created)
        self.assertEqual(eval1.id, eval2.id)
        self.assertEqual(Evaluation.objects.filter(module=module).count(), 1)
