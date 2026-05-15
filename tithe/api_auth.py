from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import authenticate
from users.models import User

class POSTokenObtainPairView(TokenObtainPairView):
    """Custom token view that validates POS PIN"""
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        pos_pin = request.data.get('pos_pin')
        
        # First authenticate with username/password
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response(
                {'error': 'Invalid credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if user has POS access role
        allowed_roles = ['admin', 'finance', 'cashier', 'treasurer', 'priest']
        if user.roles not in allowed_roles and not user.is_superuser:
            return Response(
                {'error': 'No POS access permission'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify POS PIN
        if user.pos_pin != pos_pin:
            return Response(
                {'error': 'Invalid POS PIN'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Generate tokens
        return super().post(request, *args, **kwargs)