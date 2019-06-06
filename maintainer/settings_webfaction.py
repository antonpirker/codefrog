from settings_base import *

ALLOWED_HOSTS = [
    '.codefrog.io',
]

STATIC_ROOT = '/home/ignaz/webapps/codefrog_io_static/'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'codefrog',
        'USER': 'codefrog',
        'PASSWORD': 'lqxxlXE10QHanrBIAq1y',
        'HOST': '127.0.0.1',
        'PORT': '5432',
        'CONN_MAX_AGE': 60 * 5,
    }
}


# Maintainer Setup
GIT_REPO_DIR = '/home/ignaz/webapps/codefrog_io/git_projects'