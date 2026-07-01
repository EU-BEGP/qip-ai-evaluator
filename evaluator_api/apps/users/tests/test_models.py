# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class UserManagerTests(APITestCase):
    def test_create_user_normalizes_email_and_sets_password(self):
        user = User.objects.create_user(email='test@Example.com', password='pass123')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('pass123'))
        self.assertFalse(user.is_staff)

    def test_create_user_without_password_is_unusable(self):
        user = User.objects.create_user(email='nopass@example.com')
        self.assertFalse(user.has_usable_password())

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='pass123')

    def test_create_superuser_sets_flags(self):
        user = User.objects.create_superuser(email='admin@example.com', password='pass123')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
