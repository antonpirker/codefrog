import datetime
import json
import logging
import urllib

import requests
from celery import shared_task
from dateutil.parser import parse
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from core.models import Metric, Project, Release
from core.utils import date_range, GitHub, run_shell_command
from incomingwebhooks.github.utils import get_access_token
from ingest.models import OpenIssue, Issue

logger = logging.getLogger(__name__)


@shared_task
def import_issues(project_id, repo_owner, repo_name, start_date=None):
    logger.info(
        'Project(%s): Starting import_issues. (%s)',
        project_id,
        start_date,
    )

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished import_issues.', project_id)
        return

    installation_id = project.user.profile.github_app_installation_refid
    gh = GitHub(installation_id=installation_id)

    issues = gh.get_issues(
        repo_owner=repo_owner,
        repo_name=repo_name,
        start_date=start_date,
    )

    for issue in issues:
        is_pull_request = 'pull_request' in issue
        if not is_pull_request:
            try:
                labels = [label['name'] for label in issue['labels']]
            except TypeError:
                labels = []

            opened_at = datetime.datetime.strptime(
                issue['created_at'],
                '%Y-%m-%dT%H:%M:%SZ',
            ).replace(tzinfo=timezone.utc)

            if issue['closed_at']:
                closed_at = datetime.datetime.strptime(
                    issue['closed_at'],
                    '%Y-%m-%dT%H:%M:%SZ',
                ).replace(tzinfo=timezone.utc)
            else:
                closed_at = None

            raw_issue, created = Issue.objects.update_or_create(
                project_id=project_id,
                issue_refid=issue['number'],
                opened_at=opened_at,
                defaults={
                    'closed_at': closed_at,
                    'labels': labels,
                }
            )
            logger.info(f'Issue {raw_issue}: created: {created}')

    calculate_issue_metrics.apply_async(
        kwargs={
            'project_id': project_id,
        },
    )
    logger.info(
        'Project(%s): Finished import_issues. (%s)',
        project_id,
        start_date,
    )

    return project_id


@shared_task
def import_releases(project_id, repo_owner, repo_name):
    logger.info(
        'Project(%s): Starting import_releases.',
        project_id,
    )

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished import_releases.', project_id)
        return

    installation_id = project.user.profile.github_app_installation_refid
    gh = GitHub(installation_id=installation_id)

    releases = gh.get_releases(
        repo_owner=repo_owner,
        repo_name=repo_name,
    )

    for release in releases:
        release_name = release['tag_name']
        release_date = release['published_at']
        release_url = release['html_url']

        logger.debug(
            'Project(%s): Github Release %s %s.',
            project_id,
            release_name,
            release_date,
        )
        Release.objects.update_or_create(
            project_id=project_id,
            timestamp=release_date,
            type='github_release',
            name=release_name,
            url=release_url,
        )

    logger.info(
        'Project(%s): Finished import_releases.',
        project_id,
    )
