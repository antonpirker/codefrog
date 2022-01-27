#!/usr/bin/env bash

export DEBIAN_FRONTEND=noninteractive

update-locale LC_ALL="en_US.utf8"

echo "-------------------------------------------------------------------------"
echo "###### Install generic nice stuff..." && tput sgr0 && echo ""

wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
echo "deb http://apt.postgresql.org/pub/repos/apt/ `lsb_release -cs`-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

sudo apt-get update --quiet
sudo apt-get install -y --no-install-recommends \
    postgresql-12 \
    postgresql-client-12 \
    postgresql-server-dev-12 \
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

runuser -l  postgres -c "psql -c \"CREATE ROLE codefrog with PASSWORD 'codefrog' LOGIN CREATEDB;\"" || true
runuser -l  postgres -c "psql -c \"CREATE DATABASE codefrog OWNER codefrog;\"" || true


echo "-------------------------------------------------------------------------"
echo "###### Setup dir for Git repos ..." && tput sgr0 && echo ""

mkdir -p ~/codefrog_projects_git_repos
chown vagrant.vagrant ~/codefrog_projects_git_repos
