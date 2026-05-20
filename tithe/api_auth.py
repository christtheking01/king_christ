from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import authenticate
from users.models import User


class POSTokenObtainPairView(TokenObtainPairView):
    """Custom token view that validates POS PIN and injects user data into the response."""

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        pos_pin  = request.data.get('pos_pin')

        # ── Step 1: Authenticate username + password ──────────────────────
        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ── Step 2: Check POS role ─────────────────────────────────────────
        allowed_roles = ['admin', 'finance', 'cashier', 'treasurer', 'priest',
                         'accountant', 'chairperson']
        if user.roles not in allowed_roles and not user.is_superuser:
            return Response(
                {'error': 'No POS access permission. Your role is: ' + str(user.roles)},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Step 3: Verify POS PIN ─────────────────────────────────────────
        if not user.pos_pin:
            return Response(
                {'error': 'No POS PIN configured for this account. '
                          'Please ask your administrator to set a PIN.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if str(user.pos_pin).strip() != str(pos_pin).strip():
            return Response(
                {'error': 'Invalid POS PIN'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ── Step 4: Generate JWT tokens via simplejwt ──────────────────────
        token_response = super().post(request, *args, **kwargs)

        # ── Step 5: Inject user profile into the response ──────────────────
        if token_response.status_code == 200:
            token_response.data['user'] = {
                'id':        user.id,
                'username':  user.username,
                'roles':     user.roles,
                'firstname': user.firstname or '',
                'lastname':  user.lastname  or '',
                'email':     user.email     or '',
                'phone':     user.phone     or '',
            }

        return token_response
