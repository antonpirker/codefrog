#!/usr/bin/env bash


echo "Install generic nice stuff..."

apt-get update --quiet
apt-get install -y --no-install-recommends \
    apt-transport-https \
    build-essential \
    bzip2 \
    ca-certificates \
    curl \
    gettext \
    git \
    shared-mime-info \
    vim \
    wget \
    rsync


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
