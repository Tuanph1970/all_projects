"""
JWT Authentication Module
Provides JWT token validation for protected API endpoints
"""

import jwt
from functools import wraps
from rest_framework.response import Response
from rest_framework import status


def jwt_required(view_func):
    """
    Decorator to require JWT authentication for API views.
    Extracts user information from JWT token and adds it to the request object.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Get the Authorization header
        auth_header = request.headers.get('Authorization', '')

        if not auth_header or not auth_header.startswith('Bearer '):
            # No token provided - set user to anonymous
            request.user = type('User', (), {
                'id': None,
                'is_authenticated': False
            })()
            return view_func(request, *args, **kwargs)

        # Extract the token
        token = auth_header.split(' ')[1]

        try:
            # Decode the JWT token
            payload = jwt.decode(token, 'secret_key', algorithms=['HS256'])

            # Create a user object with the decoded information
            request.user = type('User', (), {
                'id': payload.get('user_id'),
                'email': payload.get('email'),
                'is_authenticated': True
            })()

        except jwt.ExpiredSignatureError:
            return Response({
                'error': 'Token has expired'
            }, status=status.HTTP_401_UNAUTHORIZED)

        except jwt.InvalidTokenError:
            # Invalid token - set user to anonymous
            request.user = type('User', (), {
                'id': None,
                'is_authenticated': False
            })()

        return view_func(request, *args, **kwargs)

    return wrapped_view
