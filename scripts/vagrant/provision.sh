#!/usr/bin/env bash

export DEBIAN_FRONTEND=noninteractive

update-locale LC_ALL="en_US.utf8"

echo "-------------------------------------------------------------------------"
echo "###### Install generic nice stuff..." && tput sgr0 && echo ""

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


echo "-------------------------------------------------------------------------"
echo "###### Install tools for code analysis..." && tput sgr0 && echo ""

apt-get install -y --no-install-recommends \
    git \
    cloc

echo "-------------------------------------------------------------------------"
echo "###### Install prerequisites for pyenv..." && tput sgr0 && echo ""

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


echo "-------------------------------------------------------------------------"
echo "###### Install tools for running the system..." && tput sgr0 && echo ""

#apt-get install -y --no-install-recommends \
#    redis-server


echo "-------------------------------------------------------------------------"
echo "###### Setup Database ..." && tput sgr0 && echo ""

runuser -l  postgres -c "psql -c \"CREATE ROLE maintainer with PASSWORD 'maintainer' LOGIN CREATEDB;\""
runuser -l  postgres -c "psql -c \"CREATE DATABASE maintainer OWNER maintainer;\""
