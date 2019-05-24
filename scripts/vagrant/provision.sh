#!/usr/bin/env bash

update-locale LC_ALL="en_US.utf8"

echo "Install generic nice stuff..."

sudo apt-get update --quiet
sudo apt-get install -y --no-install-recommends \
    postgresql-10 \
    postgresql-client-10 \
    postgresql-server-dev-10 \
    apt-transport-https \
    build-essential \
    bzip2 \
    ca-certificates \
    curl \
    gettext \
    shared-mime-info \
    vim \
    wget \
    rsync


echo "Install tools for running the system..."

apt-get install -y --no-install-recommends \
    redis-server


echo "Install tools for code analysis..."

apt-get install -y --no-install-recommends \
    git \
    cloc


echo "Install prerequisites for pyenv..."

apt-get install -y \
    make \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libffi-dev \
    liblzma-dev

ln -s /vagrant /maintainer
