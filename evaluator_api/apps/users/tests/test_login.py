# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from unittest.mock import patch, Mock

import requests
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class Book4RLabLoginViewTests(APITestCase):
    def setUp(self):
        self.url = reverse('book4rlab_login')
        self.payload = {'email': 'user@test.com', 'password': 'pass123'}

    @patch('apps.users.services.requests.get')
    @patch('apps.users.services.requests.post')
    def test_login_success_creates_user_and_returns_tokens(self, mock_post, mock_get):
        mock_post.return_value = Mock(status_code=200, json=lambda: {'token': 'ext-token'})
        mock_get.return_value = Mock(status_code=200, json=lambda: {
            'email': 'user@test.com', 'name': 'User', 'last_name': 'Test',
        })

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(User.objects.filter(email='user@test.com').exists())

    @patch('apps.users.services.requests.post')
    def test_login_rejected_credentials_returns_401(self, mock_post):
        mock_post.return_value = Mock(status_code=401)

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('apps.users.services.requests.post', side_effect=requests.exceptions.ConnectionError)
    def test_login_connection_error_returns_503(self, mock_post):
        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch('apps.users.services.requests.post')
    def test_login_book4rlab_server_error_returns_503(self, mock_post):
        error_response = Mock(status_code=500)
        error_response.raise_for_status = Mock(side_effect=requests.exceptions.HTTPError)
        mock_post.return_value = error_response

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_login_missing_fields_returns_400(self):
        response = self.client.post(self.url, {'email': 'user@test.com'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
