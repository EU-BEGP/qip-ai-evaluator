from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import LoginInputSerializer
from .services import AuthService

class LoginProxyView(APIView):
    # Handles authentication requests via external proxy and returns JWTs
    permission_classes = [AllowAny]

    def post(self, request):
        # Processes the login request
        serializer = LoginInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        success, error_msg = AuthService.authenticate_via_external_api(email, password)
        
        if not success:
            status_code = status.HTTP_401_UNAUTHORIZED if "Invalid" in error_msg else status.HTTP_500_INTERNAL_SERVER_ERROR
            return Response({"error": error_msg}, status=status_code)

        tokens = AuthService.get_or_create_local_user(email)
        
        return Response(tokens, status=status.HTTP_200_OK)
