"""One error shape for the whole API: {"error": {"code", "message", "fields"?}}."""
import logging

from django.core.exceptions import PermissionDenied, RequestDataTooBig
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response

from .auth_cookies import clear_session_cookies, session_cookie_value

logger = logging.getLogger(__name__)


class ApiError(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'validation_error'
    default_detail = 'That is not allowed.'

    def __init__(self, code=None, message=None, status_code=None, fields=None):
        super().__init__(message or self.default_detail, code or self.default_code)
        if status_code is not None:
            self.status_code = status_code
        self.fields = fields


def validation_error(message, fields=None, code='validation_error'):
    return ApiError(code, message, status.HTTP_400_BAD_REQUEST, fields)


def not_found(message='That could not be found.'):
    return ApiError('not_found', message, status.HTTP_404_NOT_FOUND)


def _flatten(detail):
    if isinstance(detail, dict):
        out = {}
        for key, value in detail.items():
            while isinstance(value, (list, tuple)) and value:
                value = value[0]
            out[key] = _flatten(value) if isinstance(value, dict) else str(value)
        return out
    return None


def _err(code, message, http):
    return Response({'error': {'code': code, 'message': message}}, status=http)


def api_exception_handler(exc, context):
    if isinstance(exc, ApiError):
        body = {'code': exc.get_codes(), 'message': str(exc.detail)}
        if exc.fields:
            body['fields'] = exc.fields
        return Response({'error': body}, status=exc.status_code)
    if isinstance(exc, exceptions.ValidationError):
        fields = _flatten(exc.detail)
        message = 'Please check the highlighted details.' if fields else str(exc.detail[0] if isinstance(exc.detail, list) else exc.detail)
        body = {'code': 'validation_error', 'message': message}
        if fields:
            body['fields'] = fields
        return Response({'error': body}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, (exceptions.AuthenticationFailed, exceptions.NotAuthenticated)):
        response = _err('unauthenticated', 'Please log in to continue.', status.HTTP_401_UNAUTHORIZED)
        request = context.get('request')
        if request is not None and session_cookie_value(request):
            clear_session_cookies(response)  # the server no longer accepts this cookie: stop sending it
        return response
    if isinstance(exc, (exceptions.PermissionDenied, PermissionDenied)):
        return _err('permission_denied', 'You do not have permission to do that.', status.HTTP_403_FORBIDDEN)
    if isinstance(exc, (exceptions.NotFound, Http404)):
        return _err('not_found', 'That could not be found.', status.HTTP_404_NOT_FOUND)
    if isinstance(exc, exceptions.Throttled):
        return _err('rate_limited', 'Too many attempts. Please wait a moment and try again.', status.HTTP_429_TOO_MANY_REQUESTS)
    if isinstance(exc, exceptions.MethodNotAllowed):
        return _err('method_not_allowed', 'That is not supported.', status.HTTP_405_METHOD_NOT_ALLOWED)
    if isinstance(exc, exceptions.ParseError):
        return _err('validation_error', 'The request could not be read.', status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, RequestDataTooBig):
        return _err('too_large', 'That request is too large.', status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    if isinstance(exc, exceptions.UnsupportedMediaType):
        return _err('validation_error', 'Send JSON.', status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    logger.exception('Unhandled API error', exc_info=exc)
    return _err('server_error', 'Something went wrong. Please try again.', status.HTTP_500_INTERNAL_SERVER_ERROR)
