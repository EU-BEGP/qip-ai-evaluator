from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from .models import Module, Evaluation, Scan
from unittest.mock import patch
from dateutil.parser import isoparse

User = get_user_model()

class EvaluationLifecycleTests(TestCase):
    def setUp(self):
        # 1. Setup Client, User, and Module (with Valid URL)
        self.client = APIClient()
        self.user = User.objects.create_user(email="admin@upb.edu", password="password123")
        self.client.force_authenticate(user=self.user)
        self.module = Module.objects.create(
            course_key="https://learnify.se/TEST-MOD-FINAL", 
            title="Test Module"
        )
        
        self.secret = settings.RAG_CALLBACK_SECRET or "test_secret"
        self.headers = {'HTTP_X_CALLBACK_SECRET': self.secret}
        self.urls = {
            'start': reverse('start_evaluation'),
            'callback': reverse('evaluation_callback')
        }

    def _send_callback(self, eval_id, status, result=None, error=None, scan_names=None):
        """Helper to send RAG callbacks cleanly."""
        payload = {"evaluation_id": eval_id, "status": status}
        if result: payload["result"] = result
        if error: payload["error"] = error
        if scan_names: payload["scan_names"] = scan_names
        return self.client.post(self.urls['callback'], payload, format='json', **self.headers)

    @patch('apps.evaluations.services.RagService.trigger_evaluation')
    @patch('apps.evaluations.services.RagService.get_last_modified')
    def test_sequential_completion_flow(self, mock_last, mock_trigger):
        """
        SCENARIO: Request scans Individually (1 by 1) starting from scratch.
        EXPECTED: 
        1. First request CREATES the evaluation automatically.
        2. Subsequent requests REUSE it.
        3. Status remains INCOMPLETED until the VERY LAST scan is done.
        """
        # Synchronize Dates (System Date vs RAG Date)
        fixed_date_str = "2025-01-01T12:00:00Z"
        mock_last.return_value = fixed_date_str
        mock_trigger.return_value = 200
        
        # 1. Start with NO evaluation ID. The system must create it on the first call.
        current_eval_id = None
        
        all_scans = Scan.ScanType.values
        total_scans = len(all_scans)

        # 2. Loop through ALL scan types sequentially
        for i, scan_name in enumerate(all_scans):
            # A. Start the scan via API
            # CORRECCIÓN: Agregamos format='json' para que 'None' pase como 'null' válido
            resp = self.client.post(self.urls['start'], {
                "course_link": self.module.course_key, 
                "email": "admin@upb.edu",
                "scan_name": scan_name, 
                "evaluation_id": current_eval_id 
            }, format='json')
            
            self.assertEqual(resp.status_code, 202, f"Failed to start scan {scan_name}: {resp.data}")
            
            # Capture the ID returned by the backend for the next iteration
            current_eval_id = resp.data['evaluation_id']
            
            # B. Finish the scan successfully via Callback
            self._send_callback(current_eval_id, "COMPLETE", result={
                "content": [{"scan": scan_name, "data": "Done"}]
            })

            # Fetch fresh state from DB
            eval_obj = Evaluation.objects.get(id=current_eval_id)
            
            # C. Check Status Logic
            if i < total_scans - 1:
                self.assertEqual(eval_obj.status, Evaluation.Status.INCOMPLETED, 
                                 f"Evaluation should be INCOMPLETED after {i+1}/{total_scans} scans.")
            else:
                self.assertEqual(eval_obj.status, Evaluation.Status.COMPLETED, 
                                 "Evaluation should be COMPLETED only after ALL scans are done.")

    def test_partial_data_cleanup_and_failure(self):
        """
        SCENARIO: Scan sends partial data -> Then FAILS.
        EXPECTED: Partial data removed, Scan=FAILED, Eval=INCOMPLETED.
        """
        scan_type = Scan.ScanType.ASSESSMENT
        # Here we manually create because we specifically want to test the CALLBACK logic, not the start logic.
        eval_obj = Evaluation.objects.create(
            module=self.module, status=Evaluation.Status.INCOMPLETED, 
            requested_scans=[scan_type], created_at=timezone.now()
        )
        Scan.objects.create(evaluation=eval_obj, scan_type=scan_type, status=Scan.Status.IN_PROGRESS)

        # 1. Send Partial Data
        self._send_callback(eval_obj.id, "CRITERION_COMPLETE", result={
            "content": [{"scan": scan_type, "criteria": [{"name": "Part 1", "score": 5}]}]
        })
        
        # 2. Send FAILURE
        self._send_callback(eval_obj.id, "FAILED", scan_names=[scan_type], error="Crash")

        eval_obj.refresh_from_db()
        
        # Checks
        self.assertEqual(eval_obj.scans.get(scan_type=scan_type).status, Scan.Status.FAILED)
        self.assertNotEqual(eval_obj.status, Evaluation.Status.FAILED)
        
        # Check Cleanup
        scans_in_json = [x['scan'] for x in eval_obj.result_json.get('content', []) or []]
        self.assertNotIn(scan_type, scans_in_json, "Partial data must be cleaned")

    def test_all_scans_mixed_results(self):
        """
        SCENARIO: 'All Scans' requested. A succeeds, B fails.
        EXPECTED: A=COMPLETED, B=FAILED. Evaluation=IN_PROGRESS.
        """
        s_ok, s_fail = Scan.ScanType.ASSESSMENT, Scan.ScanType.MULTIMEDIA
        eval_obj = Evaluation.objects.create(
            module=self.module, status=Evaluation.Status.IN_PROGRESS, 
            requested_scans=[s_ok, s_fail], created_at=timezone.now()
        )
        Scan.objects.create(evaluation=eval_obj, scan_type=s_ok, status=Scan.Status.IN_PROGRESS)
        Scan.objects.create(evaluation=eval_obj, scan_type=s_fail, status=Scan.Status.IN_PROGRESS)

        # 1. Scan A Succeeds
        self._send_callback(eval_obj.id, "COMPLETE", result={"content": [{"scan": s_ok, "data": "Good"}]})
        
        # 2. Scan B Fails
        self._send_callback(eval_obj.id, "FAILED", scan_names=[s_fail], error="Error")

        eval_obj.refresh_from_db()
        
        # Checks
        self.assertEqual(eval_obj.scans.get(scan_type=s_ok).status, Scan.Status.COMPLETED)
        self.assertEqual(eval_obj.scans.get(scan_type=s_fail).status, Scan.Status.FAILED)
        self.assertEqual(eval_obj.status, Evaluation.Status.IN_PROGRESS)
        
        # JSON Check
        json_scans = [x['scan'] for x in eval_obj.result_json['content']]
        self.assertIn(s_ok, json_scans)
        self.assertNotIn(s_fail, json_scans)

    def test_global_failure_handling(self):
        """ SCENARIO: RAG sends generic FAILED. All running scans fail. """
        eval_obj = Evaluation.objects.create(
            module=self.module, status=Evaluation.Status.IN_PROGRESS, created_at=timezone.now()
        )
        s1 = Scan.objects.create(evaluation=eval_obj, scan_type="TypeA", status=Scan.Status.IN_PROGRESS)
        s2 = Scan.objects.create(evaluation=eval_obj, scan_type="TypeB", status=Scan.Status.COMPLETED)

        self._send_callback(eval_obj.id, "FAILED", error="System OOM")

        s1.refresh_from_db(); s2.refresh_from_db()
        self.assertEqual(s1.status, Scan.Status.FAILED)
        self.assertEqual(s2.status, Scan.Status.COMPLETED)

    def test_snapshot_callback(self):
        """ SCENARIO: Snapshot text is saved. """
        eval_obj = Evaluation.objects.create(
            module=self.module, status=Evaluation.Status.IN_PROGRESS, created_at=timezone.now()
        )
        self._send_callback(eval_obj.id, "SNAPSHOT_CREATED", result="Summary Text")
        eval_obj.refresh_from_db()
        self.assertEqual(eval_obj.document_snapshot, "Summary Text")

    @patch('apps.evaluations.services.RagService.trigger_evaluation')
    @patch('apps.evaluations.services.RagService.get_last_modified')
    def test_retry_reset_logic(self, mock_last, mock_trigger):
        """ SCENARIO: Retrying a FAILED scan resets it to IN_PROGRESS. """
        # Fix Date
        fixed_date_str = "2025-01-01T12:00:00Z"
        mock_last.return_value = fixed_date_str
        mock_trigger.return_value = 200
        fixed_date = isoparse(fixed_date_str)
        
        s_fail = Scan.ScanType.MULTIMEDIA
        # Here we create a failed state manually to setup the retry scenario
        eval_obj = Evaluation.objects.create(
            module=self.module, status=Evaluation.Status.INCOMPLETED, created_at=fixed_date
        )
        scan = Scan.objects.create(evaluation=eval_obj, scan_type=s_fail, status=Scan.Status.FAILED)

        # Retry
        resp = self.client.post(self.urls['start'], {
            "course_link": self.module.course_key, "email": "admin@upb.edu",
            "scan_name": s_fail, "evaluation_id": eval_obj.id
        }, format='json')
        
        self.assertEqual(resp.status_code, 202)
        scan.refresh_from_db()
        self.assertEqual(scan.status, Scan.Status.IN_PROGRESS)
