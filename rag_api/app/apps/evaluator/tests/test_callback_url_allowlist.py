# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.test import SimpleTestCase, override_settings

from apps.evaluator.serializers import EvaluateModuleSerializer
from apps.evaluator.security import _normalize_host, is_allowed_callback_url

ALLOWED = ["localhost", "127.0.0.1", "host.docker.internal", "eeda.iotecbol.com"]


@override_settings(ALLOWED_CALLBACK_HOSTS=ALLOWED)
class IsAllowedCallbackUrlTest(SimpleTestCase):
    """Host allowlisting must accept legitimate targets and reject every smuggling trick."""

    def test_allowed_host_with_port(self):
        self.assertTrue(is_allowed_callback_url("http://host.docker.internal:8004/evaluations/callback/"))

    def test_allowed_https_host(self):
        self.assertTrue(is_allowed_callback_url("https://eeda.iotecbol.com/evaluations/callback/"))

    def test_uppercase_host_normalizes(self):
        self.assertTrue(is_allowed_callback_url("http://LOCALHOST/x"))

    def test_disallowed_host(self):
        self.assertFalse(is_allowed_callback_url("http://evil.com/steal"))

    def test_substring_suffix_attack(self):
        self.assertFalse(is_allowed_callback_url("http://host.docker.internal.evil.com/x"))

    def test_substring_in_path_attack(self):
        self.assertFalse(is_allowed_callback_url("http://evil.com/?x=host.docker.internal"))

    def test_non_http_scheme_file(self):
        self.assertFalse(is_allowed_callback_url("file:///etc/passwd"))

    def test_non_http_scheme_gopher_ssrf(self):
        self.assertFalse(is_allowed_callback_url("gopher://127.0.0.1:6379/x"))

    def test_empty_string(self):
        self.assertFalse(is_allowed_callback_url(""))

    def test_none(self):
        self.assertFalse(is_allowed_callback_url(None))

    def test_garbage_string(self):
        self.assertFalse(is_allowed_callback_url("not a url"))

    # A full-URL allowlist entry (e.g. mirroring PUBLIC_BASE_URL) matches by host.
    @override_settings(ALLOWED_CALLBACK_HOSTS=["https://eeda.iotecbol.com/", "localhost"])
    def test_full_url_entry_matches_host(self):
        self.assertTrue(is_allowed_callback_url("https://eeda.iotecbol.com/evaluations/callback/"))

    @override_settings(ALLOWED_CALLBACK_HOSTS=["https://eeda.iotecbol.com/", "localhost"])
    def test_full_url_entry_still_rejects_other_host(self):
        self.assertFalse(is_allowed_callback_url("http://evil.com/x"))

    @override_settings(ALLOWED_CALLBACK_HOSTS=["https://eeda.iotecbol.com/", "localhost"])
    def test_bare_entry_alongside_url_entry_works(self):
        self.assertTrue(is_allowed_callback_url("http://localhost:8004/x"))


class NormalizeHostTest(SimpleTestCase):
    """Entry normalization reduces any accepted form to a bare host."""

    def test_bare_host(self):
        self.assertEqual(_normalize_host("eeda.iotecbol.com"), "eeda.iotecbol.com")

    def test_full_url(self):
        self.assertEqual(_normalize_host("https://eeda.iotecbol.com/path/"), "eeda.iotecbol.com")

    def test_host_with_port(self):
        self.assertEqual(_normalize_host("host.docker.internal:8004"), "host.docker.internal")

    def test_uppercase_lowercased(self):
        self.assertEqual(_normalize_host("EEDA.Iotecbol.COM"), "eeda.iotecbol.com")

    def test_blank_returns_none(self):
        self.assertIsNone(_normalize_host("   "))

    def test_none_returns_none(self):
        self.assertIsNone(_normalize_host(None))


@override_settings(ALLOWED_CALLBACK_HOSTS=["localhost"])
class EvaluateSerializerCallbackUrlTest(SimpleTestCase):
    """The serializer rejects a disallowed callback_url before any task is queued."""

    def _data(self, callback_url):
        return {"course_key": "ABCDE", "callback_url": callback_url}

    def test_allowed_callback_url_passes(self):
        serializer = EvaluateModuleSerializer(data=self._data("http://localhost:8004/cb/"))
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_disallowed_callback_url_rejected(self):
        serializer = EvaluateModuleSerializer(data=self._data("http://evil.com/cb/"))
        self.assertFalse(serializer.is_valid())
        self.assertIn("callback_url", serializer.errors)
