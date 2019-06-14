"""
Django settings for maintainer project.

Generated by 'django-admin startproject' using Django 2.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""
import os

def get_setting(key, default=None):
    try:
        value = os.environ[key] if key in os.environ else globals()[key]
    except KeyError:
        return default

    # cast number values
    try:
        return float(value)
    except (ValueError, TypeError):
        pass

    # cast boolean values
    if str(value).lower() == 'false':
        return False
    elif str(value).lower() == 'true':
        return True

    return value


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '4a)t=!!+!$lz82l%=*jvh&c73i288(==!vf#hij80w-5c(i1x0'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    '.ngrok.io',
    'localhost',
]


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',

    'django_extensions',
    'django_json_widget',

    'core.apps.CoreConfig',
    'ingest.apps.IngestConfig',
    'incomingwebhooks.apps.IncomingWebhooksConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'maintainer',
        'USER': 'maintainer',
        'PASSWORD': 'maintainer',
        'HOST': '127.0.0.1',
        'PORT': '5432',
        'CONN_MAX_AGE': 60 * 5,
    }
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

STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

# Logging
# https://docs.djangoproject.com/en/2.1/topics/logging/#configuring-logging

LOG_LEVEL = 'INFO'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(module)s %(pathname)s:%(lineno)d (%(funcName)s) %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
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

# settings for third party services
GITLAB_API_PERSONAL_TOKEN = get_setting('GITLAB_API_PERSONAL_TOKEN')
GITLAB_API_BASE_URL = get_setting('GITLAB_API_BASE_URL', 'https://gitlab.com/api/v4')
GITLAB_API_DEFAULT_HEADERS = {
    'Private-Token': GITLAB_API_PERSONAL_TOKEN,
}


# Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_WORKER_MAX_TASKS_PER_CHILD = 5
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 500 * 1000



# Maintainer Setup
GIT_REPO_DIR = '/git_projects'
