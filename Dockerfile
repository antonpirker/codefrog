FROM python:3.7-slim

# Setting up environment
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONUNBUFFERED=1

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

RUN touch /app/.env

# Copy application code
COPY codefrog codefrog
WORKDIR /app/codefrog/
