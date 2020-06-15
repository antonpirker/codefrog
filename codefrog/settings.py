import os

import environ
import sentry_sdk
import structlog
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from core.env import get_env

sentry_sdk.init(
    dsn="https://14e094f6e2f74dd79a36457a27ddb5a6@o400782.ingest.sentry.io/5259497",
    integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()],

    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# load environment settings and .env file
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = get_env(env.str, 'SECRET_KEY')

DEBUG = get_env(env.bool, 'DEBUG', default=True)

LIVE_SYSTEM = get_env(env.bool, 'LIVE_SYSTEM', default=False)

ALLOWED_HOSTS = get_env(env.list, 'ALLOWED_HOSTS', default=['localhost:8000', 'localhost'])


# Application definition
INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django.contrib.humanize',

    'django_extensions',
    'django_json_widget',

    'core.apps.CoreConfig',
    'connectors.apps.ConnectorsConfig',
    'engine.apps.EngineConfig',
    'web.apps.WebConfig',
    'mptt',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_structlog.middlewares.RequestMiddleware',
    'django_structlog.middlewares.CeleryMiddleware',
]

ROOT_URLCONF = 'urls'

LOGOUT_REDIRECT_URL = '/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'

CSRF_USE_SESSIONS = True
CSRF_COOKIE_HTTPONLY = True


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': get_env(
        env.db,
        'DATABASE_URL',
        default='postgres://codefrog:codefrog@127.0.0.1/codefrog?CONN_MAX_AGE=600',
    ),
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = get_env(env.str, 'STATIC_ROOT', default=os.path.join(BASE_DIR, 'staticfiles/'))

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Logging
# https://docs.djangoproject.com/en/2.1/topics/logging/#configuring-logging

LOG_LEVEL = get_env(env.str, 'LOG_LEVEL', default='INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(module)s %(pathname)s:%(lineno)d (%(funcName)s) %(message)s',
        },
        'json': {
            '()': structlog.stdlib.ProcessorFormatter,
            'processor': structlog.processors.JSONRenderer(),
        },
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'level': LOG_LEVEL,
        'handlers': ['console'],
    },
    'loggers': {
        # discard logs from...
        'faker': {
            'level': 'DEBUG',
            'handlers': ['null'],
            'propagate': False,
        },
    },
}

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.ExceptionPrettyPrinter(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=structlog.threadlocal.wrap_dict(dict),
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


# Celery
CELERY_BROKER_URL = \
    get_env(env.url, 'CELERY_BROKER_URL', default='redis://localhost:6379/0').geturl()
CELERY_RESULT_BACKEND = \
    get_env(env.url, 'CELERY_RESULT_BACKEND', default='redis://localhost:6379/1').geturl()
CELERY_WORKER_PREFETCH_MULTIPLIER = \
    get_env(env.int, 'CELERY_WORKER_PREFETCH_MULTIPLIER', default=1)
CELERY_WORKER_MAX_TASKS_PER_CHILD = \
    get_env(env.int, 'CELERY_WORKER_MAX_TASKS_PER_CHILD', default=5)
CELERY_WORKER_MAX_MEMORY_PER_CHILD = \
    get_env(env.int, 'CELERY_WORKER_MAX_MEMORY_PER_CHILD', default=500*1024)
CELERY_TASK_ALWAYS_EAGER = \
    get_env(env.bool, 'CELERY_TASK_ALWAYS_EAGER', default=DEBUG)
CELERY_CHUNK_SIZE = \
    get_env(env.int, 'CELERY_CHUNK_SIZE', default=10)
CELERY_WORKER_LOG_FORMAT = "%(asctime)s %(processName)-16s %(levelname)-8s " \
                           "%(name)s %(funcName)s:%(lineno)d %(message)s"
CELERY_WORKER_TASK_LOG_FORMAT = "%(asctime)s %(processName)-16s %(levelname)-8s " \
                                "%(task_name)s[%(task_id).8s] " \
                                "%(name)s %(funcName)s:%(lineno)d %(message)s"

# Github Setup
# TODO: can these be removed?
GITHUB_CLIENT_ID = get_env(env.str, 'GITHUB_CLIENT_ID', default=None)
GITHUB_CLIENT_SECRET = get_env(env.str, 'GITHUB_CLIENT_SECRET', default=None)


# Github App Setup
GITHUB_APP_IDENTIFIER = get_env(env.int, 'GITHUB_APP_IDENTIFIER',default= None)
GITHUB_APP_CLIENT_ID = get_env(env.str, 'GITHUB_APP_CLIENT_ID', default=None)
GITHUB_APP_CLIENT_SECRET = get_env(env.str, 'GITHUB_APP_CLIENT_SECRET', default=None)
GITHUB_AUTH_REDIRECT_URI = get_env(env.str, 'GITHUB_AUTH_REDIRECT_URI', default=None)
GITHUB_WEBHOOK_SECRET = get_env(env.str, 'GITHUB_WEBHOOK_SECRET', default=None)
try:
    GITHUB_PRIVATE_KEY = get_env(env.str, 'GITHUB_PRIVATE_KEY', multiline=True).encode()
except Exception:
    GITHUB_PRIVATE_KEY = None


# Codefrog Configuration
PROJECT_SOURCE_CODE_DIR = get_env(env.str, 'PROJECT_SOURCE_CODE_DIR', default='/tmp/git_repos')
if not os.path.exists(PROJECT_SOURCE_CODE_DIR):
    os.makedirs(PROJECT_SOURCE_CODE_DIR)
