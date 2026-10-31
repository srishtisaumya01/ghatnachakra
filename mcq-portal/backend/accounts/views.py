from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.auth_cookies import clear_session_cookies, set_session_cookies
from config.errors import ApiError, validation_error

from .models import AuthToken
from .serializers import LoginSerializer, RegisterSerializer

User = get_user_model()


def user_body(user):
    return {'id': user.pk, 'username': user.username, 'email': user.email}


def start_session(request, user, transport, status_code):
    """Issues a session for `user`. The cookie transport never puts the token in the body."""
    AuthToken.prune(user)
    raw, token = AuthToken.issue(user)
    body = {'expires_at': token.expires_at.isoformat(), 'user': user_body(user)}
    if transport == 'cookie':
        response = Response(body, status=status_code)
        set_session_cookies(request, response, raw, token)
        return response
    return Response({'token': raw, **body}, status=status_code)


class PublicAuthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


class RegisterView(PublicAuthView):
    def post(self, request):
        data = RegisterSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        if User.objects.filter(username=d['username']).exists():
            raise validation_error('That username is taken. Try another.', {'username': 'That username is taken. Try another.'}, 'username_taken')
        try:
            with transaction.atomic():
                if User.objects.filter(email__iexact=d['email']).exists():
                    raise IntegrityError
                user = User.objects.create_user(username=d['username'], email=d['email'], password=d['password'])
        except IntegrityError:
            raise validation_error('An account may already exist for that email. Try logging in.', {'email': 'Try another email, or log in.'}, 'email_taken')
        return start_session(request, user, d['transport'], status.HTTP_201_CREATED)


class LoginView(PublicAuthView):
    def post(self, request):
        data = LoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        identifier = data.validated_data['identifier']
        login_name = identifier
        if '@' in identifier:
            match = User.objects.filter(email__iexact=identifier).first()
            login_name = match.username if match else identifier
        user = authenticate(request, username=login_name, password=data.validated_data['password'])
        if user is None:
            raise ApiError('invalid_credentials', 'Username or password is incorrect.', status.HTTP_401_UNAUTHORIZED)
        return start_session(request, user, data.validated_data['transport'], status.HTTP_200_OK)


class LogoutView(APIView):
    """Ends this device's session only."""

    def post(self, request):
        request.auth.delete()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_session_cookies(response)
        return response


class MeView(APIView):
    def get(self, request):
        return Response({**user_body(request.user), 'expires_at': request.auth.expires_at.isoformat()})
