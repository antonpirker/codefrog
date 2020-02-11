import datetime
import json
import logging
import urllib
import os
from collections import defaultdict

import requests
from celery import shared_task
from dateutil.parser import parse
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from core.models import Metric, Project, Release
from core.utils import date_range, GitHub, run_shell_command
from connectors.github.utils import get_access_token
from ingest.models import OpenIssue, Issue, Complexity
from engine.models import CodeChange

logger = logging.getLogger(__name__)


@shared_task
def clone_repo(project_id, git_url, repo_dir):
    """
    Clone the remote git repository to local directory.

    If the directory already exists only a `git pull` is done.

    :return: None
    """
    logger.info('Project(%s): Starting clone_repo.', project_id)

    project = Project.objects.get(pk=project_id)

    installation_access_token = None
    if project.private:
        installation_id = project.user.profile.github_app_installation_refid
        installation_access_token = get_access_token(installation_id)

    if os.path.exists(repo_dir):
        logger.info('Project(%s): Repo Exists. Start pulling new changes.', project_id)
        cmd = f'git pull'
        run_shell_command(cmd, cwd=repo_dir)
        logger.info('Project(%s): Finished pulling new changes.', project_id)
    else:
        logger.info('Project(%s): Start cloning.', project_id)
        if installation_access_token:
            git_url = git_url.replace('https://', f'https://x-access-token:{installation_access_token}@')

        cmd = f'git clone {git_url} {repo_dir}'
        run_shell_command(cmd)
        logger.info('Project(%s): Finished cloning.', project_id)

    logger.info('Project(%s): Finished clone_repo.', project_id)

    return project_id


@shared_task
def import_code_changes(project_id, repo_dir, start_date=None):
    """
    :param project_id:
    :param repo_dir:
    :param start_date:
    :return:
    """
    logger.info('Project(%s): Starting import_code_changes(%s).', project_id, start_date)

    if isinstance(start_date, str):
        start_date = parse(start_date)
    start_date = start_date.date() if start_date else datetime.date(1970, 1, 1)

    # get first commit date
    cmd = (
        f'git rev-list --max-parents=0 HEAD '
        f' --pretty="%ad" --date=iso8601-strict-local'
    )
    output = run_shell_command(cmd, cwd=repo_dir).split('\n')[1]
    first_commit_date = parse(output).date()

    start_date = start_date if start_date >= first_commit_date else first_commit_date
    # TODO: skip the end_date, just get everything!
    end_date = start_date + datetime.timedelta(days=DAYS_PER_CHUNK)
    current_date = start_date

    logger.info(
        f'Project(%s): Running import_code_changes from %s to %s.',
        project_id,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    )

    # get git commits for date range
    cmd = (
        f'git log --reverse --date-order'
        f' --after="{start_date.strftime("%Y-%m-%d")} 00:00"'
        f' --before="{end_date.strftime("%Y-%m-%d")} 00:00"'
        f' --pretty="%ad;%H;%aN;%aE" --date=iso8601-strict-local'
    )
    output = run_shell_command(cmd, cwd=repo_dir)
    code_changes = [line for line in output.split('\n') if line]

    # TODO: here I have then all the code_changes of the whole repository.
    #  split this up so it is imported by multiple workers.
    #  for this to work, every worker needs her own copy of the repo on disk.
    #  celery chunks may be useful for this: http://docs.celeryproject.org/en/latest/userguide/canvas.html#chunks
    #  the ordering of this is not important, because we need all CodeChange to be present to run calculations on them.

    for code_change in code_changes:
        timestamp, git_commit_hash, author_name, author_email = code_change.split(';')
        timestamp = parse(timestamp)
        added, removed = get_complexity_change(repo_dir, git_commit_hash)
        file_names = list(set(list(added.keys()) + list(removed.keys())))
        try:
            for file_name in file_names:
                logger.debug('Project(%s): CodeChange %s', project_id, timestamp)
                CodeChange.objects.update_or_create(
                    project_id=project_id,
                    timestamp=timestamp,
                    file_path=file_name,
                    author=f'{author_name} <{author_email}>',
                    complexity_added=added[file_name],
                    complexity_removed=removed[file_name],
                )
        except ValueError as err:
            logger.error('Project(%s): Error saving CodeChange: %s', project_id, err)
        current_date = timestamp.date() \
            if timestamp.date() > current_date else current_date

    # TODO: this should then be started otherwise, but the basic function of calculate_code_metrics stays the same.
    # TODO: check how fast this calculate_code_metrics is.
    # Calculate code metrics for this chunk.
    calculate_code_metrics.apply_async(kwargs={
        'project_id': project_id,
        'start_date': start_date,
    })

    # TODO: this can then be ommited
    # Get last commit
    cmd = 'git log --pretty="%ad" --date-order --date=iso8601-strict-local -1'
    output = run_shell_command(cmd, cwd=repo_dir)
    last_commit_date = parse(output).date()

    # If we are not at the end, start ingesting the next chunk
    if current_date < last_commit_date:
        if start_date <= current_date:
            current_date = end_date
        logger.info(
            'Project(%s): Calling import_code_changes for next chunk. (start_date=%s)',
            project_id,
            current_date,
        )
        import_code_changes.apply_async(kwargs={
            'project_id': project_id,
            'repo_dir': repo_dir,
            'start_date': current_date,
        })

    logger.info('Project(%s): Finished import_code_changes(%s).', project_id, start_date)

    return project_id


@shared_task
def import_tags(project_id):
    logger.info(
        'Project(%s): Starting import_tags.',
        project_id,
    )

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished import_releases.', project_id)
        return

    cmd = (
        f'git tag --list '
        f'--format "%(refname:strip=2);%(taggerdate);%(committerdate)"'
    )
    output = run_shell_command(cmd, cwd=project.repo_dir)
    tags = [line for line in output.split('\n') if line]

    for tag in tags:
        tag_name, tagger_date, committer_date = tag.split(';')

        try:
            tagger_date = parse(tagger_date)
        except ValueError:
            tagger_date = None

        try:
            committer_date = parse(committer_date)
        except ValueError:
            committer_date = None

        tag_date = tagger_date or committer_date

        logger.debug(
            'Project(%s): Git Tag %s %s',
            project_id,
            tag_name,
            tag_date,
        )
        Release.objects.update_or_create(
            project_id=project_id,
            timestamp=tag_date,
            type='git_tag',
            name=tag_name,
        )

    logger.info('Project(%s): Finished import_tags.', project_id)

    return project_id
