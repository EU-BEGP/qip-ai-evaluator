import requests
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthService:
    # Encapsulates business logic for authentication
    
    @staticmethod
    def authenticate_via_external_api(email, password):
        # Proxies credentials to the external API to validate identity
        try:
            response = requests.post(
                settings.EXTERNAL_LOGIN_API_URL, 
                data={'email': email, 'password': password},
                timeout=30
            )
            response.raise_for_status()
            return True, None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (401, 400):
                return False, "Invalid credentials"
            return False, f"Error from auth server: {str(e)}"
        except requests.exceptions.RequestException as e:
            return False, f"Could not connect to auth server: {str(e)}"

    @staticmethod
    def get_or_create_local_user(email):
        # Ensures local user existence and generates JWT tokens
        user, created = User.objects.get_or_create(email=email)
        if created:
            user.set_unusable_password()
            user.save()
        
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
