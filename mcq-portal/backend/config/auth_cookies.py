"""The browser session cookies: one place that sets, reads and clears them.

A browser signs in with `transport: "cookie"`; the server then sets the SESSION cookie (HttpOnly, Secure in production,
SameSite=Strict, path /api/) and Django's CSRF cookie (readable by the page, echoed in X-CSRFToken). The token is never in a
response body for the cookie transport, so page script never holds the credential.
"""
from django.conf import settings
from django.middleware.csrf import rotate_token
from django.utils import timezone


def session_cookie_value(request):
    return request.COOKIES.get(settings.AUTH_COOKIE_NAME)


def set_session_cookies(request, response, raw_token, token):
    seconds = max(0, int((token.expires_at - timezone.now()).total_seconds()))
    response.set_cookie(settings.AUTH_COOKIE_NAME, raw_token, max_age=seconds, path=settings.AUTH_COOKIE_PATH,
                        secure=settings.AUTH_COOKIE_SECURE, httponly=True, samesite=settings.AUTH_COOKIE_SAMESITE)
    rotate_token(request)  # a fresh CSRF secret for the new session; CsrfViewMiddleware writes its cookie onto this response


def clear_session_cookies(response):
    response.delete_cookie(settings.AUTH_COOKIE_NAME, path=settings.AUTH_COOKIE_PATH, samesite=settings.AUTH_COOKIE_SAMESITE)
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path=settings.CSRF_COOKIE_PATH, samesite=settings.CSRF_COOKIE_SAMESITE)
