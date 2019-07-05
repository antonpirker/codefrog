from settings_base import *

import os

ALLOWED_HOSTS = [
    '.codefrog.io',
]

STATIC_ROOT = '/home/codefrog/webapps/codefrog_io_static/'

DB_PASSWORD = os.environ['CODEFROG_DB_PASSWORD'] \
    if 'CODEFROG_DB_PASSWORD' in os.environ else 'codefrog'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'codefrog',
        'USER': 'codefrog',
        'PASSWORD': DB_PASSWORD,
        'HOST': '127.0.0.1',
        'PORT': '5432',
        'CONN_MAX_AGE': 60 * 5,
    }
}


# Maintainer Setup
GIT_REPO_DIR = '/home/codefrog/webapps/codefrog_io/git_projects'