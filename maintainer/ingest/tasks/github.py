import datetime
import json
import logging
import urllib

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from core.models import Metric, Release
from ingest.models import OpenIssue

logger = logging.getLogger(__name__)

DAYS_PER_CHUNK = 30
PAGES_PER_CHUNK = 5

GITHUB_ISSUES_PER_PAGE = 100

GITHUB_API_BASE_URL = 'https://api.github.com'
GITHUB_API_DEFAULT_HEADERS = {
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'Maintainer',
}

GITHUB_API_DEFAULT_PARAMS = {
    'client_id': settings.GITHUB_CLIENT_ID,
    'client_secret': settings.GITHUB_CLIENT_SECRET,
}

GITHUB_BUG_ISSUE_LABELS = [
    'Bug',
    'bug',
    'type:bug/performance',
    'Type: bug',
    'kind/bug',
    'bug', 'debt', 'perf-bloat', 'regression',
    'crash', 'data-loss', 'regression', 'uncaught-exception',
    'regression',
]


@shared_task
def ingest_open_github_issues(project_id, repo_owner, repo_name):
    logger.info('Project(%s): Starting ingest_open_github_issues.', project_id)

    params = GITHUB_API_DEFAULT_PARAMS
    params.update({
        'state': 'open',
        'sort': 'created',
        'direction': 'asc',
        'per_page': str(GITHUB_ISSUES_PER_PAGE),
    })

    list_issues_url = f'/repos/{repo_owner}/{repo_name}/issues'
    url = f'{GITHUB_API_BASE_URL}{list_issues_url}?%s' % urllib.parse.urlencode(params)

    while url:
        r = requests.get(url, headers=GITHUB_API_DEFAULT_HEADERS)
        if r.status_code != 200:
            logger.error('Error %s: %s (%s) for Url: %s', r.status_code, r.content, r.reason, url)
            # retry
            ingest_open_github_issues.apply_async(
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

                OpenIssue.objects.update_or_create(
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

    logger.info('Project(%s): Finished ingest_open_github_issues.', project_id)


@shared_task
def ingest_github_issues(project_id, repo_owner, repo_name):
    logger.info('Project(%s): Starting ingest_github_issues.', project_id)

    params = GITHUB_API_DEFAULT_PARAMS
    params.update({
        'state': 'open',
        'sort': 'created',
        'direction': 'asc',
        'per_page': str(GITHUB_ISSUES_PER_PAGE),
    })

    list_issues_url = f'/repos/{repo_owner}/{repo_name}/issues'
    url = f'{GITHUB_API_BASE_URL}{list_issues_url}?%s' % urllib.parse.urlencode(params)

    while url:
        r = requests.get(url, headers=GITHUB_API_DEFAULT_HEADERS)
        if r.status_code != 200:
            logger.error('Error %s: %s (%s) for Url: %s', r.status_code, r.content, r.reason, url)
            # retry
            ingest_github_issues.apply_async(
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

                OpenIssue.objects.update_or_create(
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

    calculate_github_issue_metrics(
        project_id=project_id,
        query_date=timezone.now().date(),
    )
    logger.info('Project(%s): Finished ingest_github_issues.', project_id)


@shared_task
def calculate_github_issue_metrics(project_id, query_date=None):
    logger.info('Project(%s): Starting calculate_github_issue_metrics (query_date=%s).', project_id, query_date.strftime("%Y-%m-%d") if query_date else query_date)

    query_date = query_date if query_date else datetime.date(1970, 1, 1)

    issues = OpenIssue.objects.filter(
        project_id=project_id,
        query_time__date=query_date,
    )

    num_bugs = 0

    for issue in issues:
        is_bug = bool({str.casefold(x) for x in GITHUB_BUG_ISSUE_LABELS} &
                      {str.casefold(x) for x in issue.labels})

        if is_bug:
            num_bugs += 1

    metric, _ = Metric.objects.get_or_create(
        project_id=project_id,
        date=query_date,
    )

    metric_json = metric.metrics
    if not metric_json:
        metric_json = {}
    metric_json['github_bug_issues_open'] = num_bugs
    metric_json['github_other_issues_open'] = len(issues) - num_bugs
    metric.metrics = metric_json
    metric.save()

    logger.info('Project(%s): Finished calculate_github_issue_metrics (query_date=%s).', project_id, query_date.strftime("%Y-%m-%d") if query_date else query_date)


@shared_task
def ingest_github_releases(project_id, repo_owner, repo_name, page=1):
    logger.info('Project(%s): Starting ingest_github_releases.', project_id)

    params = GITHUB_API_DEFAULT_PARAMS
    params.update({
        'per_page': str(GITHUB_ISSUES_PER_PAGE),
        'page': page,
    })

    list_tags_url = f'/repos/{repo_owner}/{repo_name}/releases'
    url = f'{GITHUB_API_BASE_URL}{list_tags_url}?%s' % urllib.parse.urlencode(params)

    pages_processed = 0

    while url:
        r = requests.get(url, headers=GITHUB_API_DEFAULT_HEADERS)
        releases = json.loads(r.content)

        for release in releases:
            tag_name = release['tag_name']
            tag_date = release['published_at']
            tag_url = release['html_url']

            logger.debug(
                'Project(%s): Github Release %s %s.',
                project_id,
                tag_name,
                tag_date,
            )
            Release.objects.update_or_create(
                project_id=project_id,
                timestamp=tag_date,
                type='github_release',
                name=tag_name,
                url=tag_url,
            )

        url = None
        try:
            links = requests.utils.parse_header_links(r.headers['Link'])
            for link in links:
                if link['rel'] == 'next':
                    url = link['url']
                    break
        except KeyError:
            pass

        pages_processed += 1
        if pages_processed >= PAGES_PER_CHUNK:
            ingest_github_releases.apply_async(
                kwargs={
                    'project_id': project_id,
                    'repo_owner': repo_owner,
                    'repo_name': repo_name,
                    'page': page + pages_processed,
                }
            )
            return

    logger.info('Project(%s): Finished ingest_github_releases.', project_id)
