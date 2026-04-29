# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import requests
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
User = get_user_model()

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def user_remote_login(email, password):
        """Exchange email/password for a Book4RLab token."""

        url = getattr(settings, 'EXTERNAL_LOGIN_API_URL', None)
        if not url:
            logger.critical("EXTERNAL_LOGIN_API_URL is missing in settings.")
            return None
        
        payload = {"email": email, "password": password}
        
        try:
            logger.info("Attempting remote login")
            logger.debug(f"Remote login for {email}")
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info(f"Remote login successful.")
                return response.json().get('token')
            
            logger.warning(f"Failed remote login for user: {response.status_code}")
            return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error during Book4RLab login: {str(e)}")
            return None

    @staticmethod
    def user_get_and_sync(external_token):
        """Use token to get profile and sync local User with Book4RLab User."""

        url = getattr(settings, 'EXTERNAL_AUTH_ME_URL', None)
        if not url:
            logger.critical("EXTERNAL_AUTH_ME_URL missing in settings.")
            return None
        
        headers = {'Authorization': f'token {external_token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch profile. Status: {response.status_code}")
                return None
            
            data = response.json()
            email = data.get('email')

            if not email:
                logger.error("External profile response missing 'email'.")
                return None

            user, created = User.objects.update_or_create(
                email=email,
                defaults={
                    'first_name': data.get('name', ''),
                    'last_name': data.get('last_name', ''),
                    'country': data.get('country', ''),
                    'time_zone': data.get('time_zone', ''),
                    'external_id': data.get('id'),
                }
            )
            
            if created:
                logger.info(f"Created new local user")

            else:
                updated_fields = []

                retrieved_fields = [
                    ('first_name', data.get('name', '')),
                    ('last_name', data.get('last_name', '')),
                    ('country', data.get('country', '')),
                    ('time_zone', data.get('time_zone', '')),
                ]

                for field, value in retrieved_fields:
                    if getattr(user, field) != value:
                        setattr(user, field, value)
                        updated_fields.append(field)

                if updated_fields:
                    user.save(update_fields = updated_fields)
                    logger.info("Synchronized changed fields for user")
                else:
                    logger.debug(f"No changes detected for user {email}. Skipping database update.")
                
            return user
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Profile Sync Error: {e}")
            return None
