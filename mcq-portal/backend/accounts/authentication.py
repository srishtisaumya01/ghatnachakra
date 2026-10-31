from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from rest_framework import authentication, exceptions

from config.auth_cookies import session_cookie_value
from config.errors import ApiError

from .models import AuthToken, hash_token

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


class TokenAuthentication(authentication.BaseAuthentication):
    """The session token, from `Authorization: Bearer <token>` (scripts) or from the HttpOnly session cookie (browsers).
    A request authenticated ONLY by the cookie must pass Django's CSRF check for anything that changes data."""

    keyword = 'Bearer'

    def authenticate(self, request):
        raw, via_cookie = self._credential(request)
        if raw is None:
            return None
        token = AuthToken.objects.select_related('user').filter(key_hash=hash_token(raw)).first()
        now = timezone.now()
        if token is None or token.expires_at <= now or not token.user.is_active:
            raise exceptions.AuthenticationFailed()
        if via_cookie and request.method not in SAFE_METHODS:
            try:
                authentication.SessionAuthentication().enforce_csrf(request)
            except (exceptions.PermissionDenied, PermissionDenied):
                raise ApiError('csrf_failed', 'Your session could not be verified. Reload the page and try again.', 403)
        if token.last_used_at is None or now - token.last_used_at > timedelta(hours=1):
            AuthToken.objects.filter(pk=token.pk).update(last_used_at=now)
        return token.user, token

    def authenticate_header(self, request):
        return self.keyword

    def _credential(self, request):
        parts = authentication.get_authorization_header(request).split()
        if parts and parts[0].lower() == self.keyword.lower().encode():
            if len(parts) != 2:
                raise exceptions.AuthenticationFailed()
            try:
                return parts[1].decode(), False
            except UnicodeError:
                raise exceptions.AuthenticationFailed()
        cookie = session_cookie_value(request)
        return (cookie, True) if cookie else (None, False)
