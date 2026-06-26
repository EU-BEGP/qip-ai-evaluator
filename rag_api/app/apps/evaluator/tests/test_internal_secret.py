# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.test import SimpleTestCase, override_settings

from apps.evaluator.security import HasInternalSecret


@override_settings(RAG_INBOUND_SECRET="topsecret")
class HasInternalSecretTest(SimpleTestCase):
    """Inbound permission accepts only the exact shared secret."""

    class _FakeRequest:
        def __init__(self, secret=None):
            self.headers = {} if secret is None else {"X-Internal-Secret": secret}

    def setUp(self):
        self.perm = HasInternalSecret()

    def test_correct_secret_allowed(self):
        self.assertTrue(self.perm.has_permission(self._FakeRequest("topsecret"), None))

    def test_wrong_secret_denied(self):
        self.assertFalse(self.perm.has_permission(self._FakeRequest("nope"), None))

    def test_missing_header_denied(self):
        self.assertFalse(self.perm.has_permission(self._FakeRequest(), None))

    def test_empty_header_denied(self):
        self.assertFalse(self.perm.has_permission(self._FakeRequest(""), None))
