FROM python:3-slim

# Setting up environment
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONUNBUFFERED=1

ARG SECRET_KEY="well-known-not-secret-key"
ENV SECRET_KEY=$SECRET_KEY

ARG DATABASE_URL="postgres://dbuser:dbuser@localhost/dbname?CONN_MAX_AGE=600"
ENV DATABASE_URL=$DATABASE_URL

ARG CELERY_BROKER_URL="redis://localhost:6379/0"
ENV CELERY_BROKER_URL=$CELERY_BROKER_URL

WORKDIR /app

# Install dependencies
RUN apt-get update -qy \
    && apt-get install -qy --no-install-recommends \
        git-core \
        libpq-dev \
        make \
        automake \
        gcc \
        g++ \
        subversion \
        python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Copy application code
COPY maintainer maintainer

# Silence warning about the missing .env file
RUN touch /app/.env

WORKDIR /app/maintainer/

#RUN python ./manage.py migrate \
#    && python ./manage.py collectstatic  \
#    && find . -name "*.pyc" -exec rm -f {} \;

RUN python ./manage.py collectstatic

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "8", "wsgi:application"]
