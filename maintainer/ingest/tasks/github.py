import datetime
import json
import logging
import urllib

import requests
from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from core.models import Metric, Release
from core.utils import daterange
from ingest.models import OpenIssue, RawIssue

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
def ingest_raw_github_issues(project_id, repo_owner, repo_name, start_date=None):
    logger.info('Project(%s): Starting ingest_raw_github_issues.', project_id)

    params = GITHUB_API_DEFAULT_PARAMS
    params.update({
        'state': 'all',
        'sort': 'created',
        'direction': 'asc',
        'per_page': str(GITHUB_ISSUES_PER_PAGE),
    })

    if start_date:
        params['since'] = start_date.isoformat()

    list_issues_url = f'/repos/{repo_owner}/{repo_name}/issues'
    url = f'{GITHUB_API_BASE_URL}{list_issues_url}?%s' % urllib.parse.urlencode(params)

    while url:
        r = requests.get(url, headers=GITHUB_API_DEFAULT_HEADERS)
        if r.status_code != 200:
            logger.error('Error %s: %s (%s) for Url: %s', r.status_code, r.content, r.reason, url)
            # retry
            ingest_raw_github_issues.apply_async(
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

                RawIssue.objects.update_or_create(
                    project_id=project_id,
                    issue_refid=issue['number'],
                    opened_at=opened_at,
                    defaults={
                        'closed_at': closed_at,
                        'labels': labels,
                    }
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

    calculate_github_issue_metrics.apply_async(
        kwargs={
            'project_id': project_id,
        },
    )
    logger.info('Project(%s): Finished ingest_raw_github_issues.', project_id)


@shared_task
def calculate_github_issue_metrics(project_id):
    logger.info('Project(%s): Starting calculate_github_issue_metrics.', project_id)

    issues = RawIssue.objects.filter(
        project_id=project_id,
    ).order_by('opened_at', 'closed_at')

    start_date = issues.first().opened_at
    end_date = timezone.now()

    for day in daterange(start_date, end_date):
        # open issues
        open_issues = issues.filter(
            Q(opened_at__date__lte=day)
            & (Q(closed_at__isnull=True) | Q(closed_at__date__gte=day))
        )
        count_open_issues = open_issues.count()
        age_opened_issues = sum([i.get_age(at_date=day) for i in open_issues])

        # closed issues
        closed_issues = issues.filter(closed_at__isnull=False, closed_at__date__lte=day)
        count_closed_issues = closed_issues.count()
        age_closed_issues = sum([i.get_age() for i in closed_issues])

        # age
        try:
            age = (age_closed_issues+age_opened_issues)/(count_closed_issues+count_open_issues)
        except ZeroDivisionError:
            age = 0

        metric, _ = Metric.objects.get_or_create(
            project_id=project_id,
            date=day,
        )

        metric_json = metric.metrics
        if not metric_json:
            metric_json = {}
        metric_json['github_issues_open'] = count_open_issues
        metric_json['github_issue_age'] = age
        metric.metrics = metric_json
        metric.save()

    logger.info('Project(%s): Finished calculate_github_issue_metrics.', project_id)


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
