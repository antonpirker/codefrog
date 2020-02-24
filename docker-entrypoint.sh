#!/bin/bash
set -e

# first collect all static files into one place
./manage.py collectstatic --clear --noinput

# then start the given command
exec "$@"
