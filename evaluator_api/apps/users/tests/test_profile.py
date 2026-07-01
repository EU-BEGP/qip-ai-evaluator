# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .conftest import make_user


class UserProfileMeViewTests(APITestCase):
    def setUp(self):
        self.user = make_user(email='me@test.com', first_name='Me')
        self.url = reverse('user_profile_me')

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_own_profile(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'me@test.com')
        self.assertEqual(response.data['first_name'], 'Me')


class UserProfileDetailViewTests(APITestCase):
    def setUp(self):
        self.staff = make_user(email='staff@test.com', is_staff=True)
        self.regular = make_user(email='regular@test.com')
        self.target = make_user(email='target@test.com')
        self.url = reverse('user_profile_detail', kwargs={'pk': self.target.pk})

    def test_staff_can_view_any_profile(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'target@test.com')

    def test_non_staff_is_denied(self):
        self.client.force_authenticate(self.regular)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_user_returns_404(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(reverse('user_profile_detail', kwargs={'pk': 999999}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
