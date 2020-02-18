#!/bin/bash
set -e

# first collect all static files into one place
./manage.py collectstatic

# then start the given command
exec "$@"
