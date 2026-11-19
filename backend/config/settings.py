from pathlib import Path
import os
import sys
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
CAMUNDA_URL = '' if 'test' in sys.argv else os.getenv('CAMUNDA_URL', '')
CAMUNDA_USER = os.getenv('CAMUNDA_USER', '')
CAMUNDA_PASSWORD = os.getenv('CAMUNDA_PASSWORD', '')


def _env_bool(name, default):
    return os.getenv(name, default).strip().lower() in ('true', '1', 'yes', 'on')


def _env_list(name, default=''):
    value = os.getenv(name, '').strip() or default
    return [item.strip() for item in value.split(',') if item.strip()]


DEBUG = _env_bool('DJANGO_DEBUG', 'false')
TESTING = 'test' in sys.argv
SECRET_KEY = (os.getenv('DJANGO_SECRET_KEY') or '').strip()
if not SECRET_KEY and (DEBUG or TESTING):
    SECRET_KEY = 'sinac-local-development-only-key-change-before-deployment-2026'
if not DEBUG and len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY debe configurarse con al menos 50 caracteres cuando DEBUG está desactivado.'
    )
ALLOWED_HOSTS = _env_list('DJANGO_ALLOWED_HOSTS', '*' if DEBUG else 'localhost,127.0.0.1,[::1],backend')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'preregistro',
]

MIDDLEWARE = [
    'preregistro.historial.limpiar_actor_middleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'camunda'),
        'USER': os.getenv('DB_USER', 'camunda'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'camunda' if DEBUG else ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5433' if os.getenv('DB_HOST') is None else '5432'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'sinac_cache',
    }
}

AUTH_USER_MODEL = 'preregistro.Aspirante'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'preregistro.historial.HistorialJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'preregistro.paginacion.PaginacionOpcional',
    'PAGE_SIZE': 50,
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10000/minute' if TESTING else os.getenv('THROTTLE_ANON', '120/minute'),
        'user': '10000/minute' if TESTING else os.getenv('THROTTLE_USER', '1200/minute'),
        'login': '10000/minute' if TESTING else os.getenv('THROTTLE_LOGIN', '10/minute'),
        'registro': '10000/minute' if TESTING else os.getenv('THROTTLE_REGISTRO', '5/hour'),
        'refresh': '10000/minute' if TESTING else os.getenv('THROTTLE_REFRESH', '30/minute'),
        'recuperacion': '10000/minute' if TESTING else os.getenv('THROTTLE_RECUPERACION', '5/hour'),
        'verificacion': '10000/minute' if TESTING else os.getenv('THROTTLE_VERIFICACION', '30/minute'),
    },
    'NUM_PROXIES': int(os.getenv('DJANGO_NUM_PROXIES', '1')),
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(minutes=int(os.getenv('JWT_ACCESS_MINUTES', '30'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=int(os.getenv('JWT_REFRESH_HOURS', '24'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}

CORS_ALLOWED_ORIGINS = _env_list('DJANGO_CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
CORS_ALLOW_CREDENTIALS = False
CSRF_TRUSTED_ORIGINS = _env_list('DJANGO_CSRF_TRUSTED_ORIGINS', ','.join(CORS_ALLOWED_ORIGINS))

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 8 * 60 * 60
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

HTTPS = _env_bool('DJANGO_HTTPS', 'false')
if HTTPS:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = _env_bool('DJANGO_SSL_REDIRECT', 'true')
    SECURE_REDIRECT_EXEMPT = [r'^health/$']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool('DJANGO_HSTS_SUBDOMAINS', 'true')
    SECURE_HSTS_PRELOAD = _env_bool('DJANGO_HSTS_PRELOAD', 'false')

EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = _env_bool('EMAIL_USE_TLS', 'true')
EMAIL_USE_SSL = _env_bool('EMAIL_USE_SSL', 'false')
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-responder@sinac.local')
PASSWORD_RESET_TIMEOUT = int(os.getenv('PASSWORD_RESET_SECONDS', '3600'))
SINAC_URL_PUBLICA = os.getenv('SINAC_URL_PUBLICA', 'http://localhost:3000').rstrip('/')
if DEBUG and not EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'sinac': {'format': '%(asctime)s %(levelname)s %(name)s %(message)s'},
    },
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'sinac'}},
    'loggers': {
        'django.security': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
        'preregistro': {'handlers': ['console'], 'level': 'ERROR' if TESTING else os.getenv('DJANGO_LOG_LEVEL', 'INFO')},
    },
}

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
