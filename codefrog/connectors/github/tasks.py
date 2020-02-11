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
def import_open_issues(project_id, repo_owner, repo_name):
    logger.info('Project(%s): Starting import_open_issues.', project_id)

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished import_open_issues.', project_id)
        return

    installation_access_token = None
    if project.private:
        installation_id = project.user.profile.github_app_installation_refid
        installation_access_token = get_access_token(installation_id)

    # Delete all old open issues of today
    OpenIssue.objects.filter(
        project_id=project_id,
        query_time__date=timezone.now().date(),
    ).delete()

    headers = {
        'Accept': 'application/vnd.github.machine-man-preview+json',
        'Authorization': 'token %s' % installation_access_token,
    }

    params = {
        'state': 'open',
        'sort': 'created',
        'direction': 'asc',
        'per_page': str(GITHUB_ISSUES_PER_PAGE),
    }

    list_issues_url = f'/repos/{repo_owner}/{repo_name}/issues'
    url = f'{GITHUB_API_BASE_URL}{list_issues_url}?%s' % urllib.parse.urlencode(params)

    while url:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            logger.error('Error %s: %s (%s) for Url: %s', r.status_code, r.content, r.reason, url)
            # retry
            import_open_issues.apply_async(
                kwargs={
                    'project_id': project_id,
                    'repo_owner': repo_owner,
                    'repo_name': repo_name,
                },
                countdown=10,
            )
            return

        issues = json.loads(r.content)

        for issue in issues:
            is_pull_request = 'pull_request' in issue
            if not is_pull_request:
                try:
                    labels = [label['name'] for label in issue['labels']]
                except TypeError:
                    labels = []

                OpenIssue.objects.create(
                    project_id=project_id,
                    query_time=timezone.now(),
                    issue_refid=issue['number'],
                    labels=labels,
                )

        # get url of next page (if any)
        url = None
        try:
            links = requests.utils.parse_header_links(r.headers['Link'])
            for link in links:
                if link['rel'] == 'next':
                    url = link['url']
                    break
        except KeyError:
            pass

    # Also import the issues from the last 24 hours
    # to calculate the updated average age of issues.
    start_date = (timezone.now() - datetime.timedelta(days=1))\
        .replace(hour=0, minute=0, second=0, microsecond=0)
    import_issues.apply_async(
        kwargs={
            'project_id': project_id,
            'repo_owner': repo_owner,
            'repo_name': repo_name,
            'start_date': start_date,
        }
    )

    logger.info('Project(%s): Finished import_open_issues.', project_id)

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
