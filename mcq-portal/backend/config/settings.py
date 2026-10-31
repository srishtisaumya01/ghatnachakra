"""Ghatnachakra API settings.

Everything environment-specific comes from environment variables (optionally a git-ignored ``backend/.env``, see
``.env.example``). The app and the API are ONE origin for the browser: the frontend host (Vercel) rewrites ``/api/*`` to this
server, and ``web/dev.py`` does the same locally, so the session cookie is first-party and nothing needs CORS.
"""
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    """Minimal KEY=VALUE reader so local setup needs no extra package. The real environment wins."""
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / '.env')


def _flag(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {'1', 'true', 'yes', 'on'}


def _list(name, default=''):
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


DEBUG = _flag('DJANGO_DEBUG', False)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('Set DJANGO_SECRET_KEY (or DJANGO_DEBUG=true for local development only).')
    SECRET_KEY = 'insecure-local-development-key-do-not-use-anywhere-else'

ALLOWED_HOSTS = _list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1' if DEBUG else '')
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('Set DJANGO_ALLOWED_HOSTS (comma-separated host names) when DJANGO_DEBUG is off.')

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',
    'accounts',
    'quiz',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'


def _postgres_from_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {'postgres', 'postgresql'}:
        raise ImproperlyConfigured('DATABASE_URL must be a postgres:// or postgresql:// URL.')
    pooled = '-pooler.' in (parsed.hostname or '')
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(parsed.path.lstrip('/')),
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port or ''),
        'OPTIONS': dict(parse_qsl(parsed.query)),
        'CONN_MAX_AGE': 0 if pooled else 60,
        'CONN_HEALTH_CHECKS': not pooled,
        'DISABLE_SERVER_SIDE_CURSORS': pooled,
    }


DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
DATABASES = {
    'default': _postgres_from_url(DATABASE_URL) if DATABASE_URL else {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DB_PATH', str(BASE_DIR / 'db.sqlite3')),
        'OPTIONS': {'timeout': 20, 'transaction_mode': 'IMMEDIATE', 'init_command': 'PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;'},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['accounts.authentication.TokenAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
    'EXCEPTION_HANDLER': 'config.errors.api_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {'auth': os.environ.get('DJANGO_AUTH_THROTTLE', '30/min')},
    'UNAUTHENTICATED_USER': None,
    'NUM_PROXIES': 0,
}

# Opaque session tokens: stored hashed, expire, revoked on logout. Browsers carry theirs in an HttpOnly cookie that is only
# sent to /api/ (config/auth_cookies.py, accounts/authentication.py), exactly as in Arcloop.
AUTH_TOKEN_LIFETIME_DAYS = int(os.environ.get('DJANGO_TOKEN_LIFETIME_DAYS', '14'))
AUTH_COOKIE_NAME = 'ghatnachakra_session'
AUTH_COOKIE_PATH = '/api/'
AUTH_COOKIE_SAMESITE = 'Strict'
AUTH_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_NAME = 'ghatnachakra_csrf'
CSRF_COOKIE_PATH = '/'
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_HTTPONLY = False  # the page must echo it in X-CSRFToken
CSRF_COOKIE_AGE = AUTH_TOKEN_LIFETIME_DAYS * 24 * 3600

# The browser's Origin is the FRONTEND's address (a Vercel rewrite keeps it) while Host is this server's, so Django's
# CSRF origin check must be told that the frontend is a trusted origin.
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5174' if DEBUG else '').rstrip('/')
if not DEBUG and not FRONTEND_URL.startswith('https://'):
    raise ImproperlyConfigured('Set FRONTEND_URL to the https:// address of the frontend (e.g. https://ghatnachakra.vercel.app).')
CSRF_TRUSTED_ORIGINS = sorted({o for o in [FRONTEND_URL, *_list('DJANGO_CSRF_TRUSTED_ORIGINS')] if o})

# Question bank (data/) and the source books (PDFs) used to render crops of the original page.
DATA_DIR = Path(os.environ.get('GHATNACHAKRA_DATA_DIR', str(BASE_DIR.parent / 'data')))
BOOKS_DIR = Path(os.environ.get('GHATNACHAKRA_BOOKS_DIR', str(BASE_DIR.parent.parent)))
CROP_CACHE_DIR = Path(os.environ.get('GHATNACHAKRA_CROP_CACHE', str(BASE_DIR / 'cache')))

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = _flag('DJANGO_SECURE_SSL_REDIRECT', True)
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '0'))
    if _flag('DJANGO_BEHIND_PROXY', False):  # Render terminates TLS and sets X-Forwarded-Proto
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
        REST_FRAMEWORK['NUM_PROXIES'] = 2  # Vercel's rewrite, then Render's router

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'plain': {'format': '%(asctime)s %(levelname)s %(name)s %(message)s'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'}},
    'root': {'handlers': ['console'], 'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO')},
}

if len(sys.argv) > 1 and sys.argv[1] == 'test':
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
