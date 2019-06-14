import datetime
import json
import logging
import os
import urllib
from collections import defaultdict

import pandas as pd
import requests
from celery import shared_task
from dateutil.parser import parse

from core.models import Metric, Release
from ingest.models import RawIssue

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
    'client_id': os.environ['GITHUB_CLIENT_ID'],
    'client_secret': os.environ['GITHUB_CLIENT_SECRET'],
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
def ingest_github_issues(project_id, repo_owner, repo_name, page=1):
    logger.info('Project(%s): Starting ingest_github_issues. (Page: %s)', project_id, page)

    params = GITHUB_API_DEFAULT_PARAMS
    params.update({
        'state': 'all',
        'sort': 'updated',
        'direction': 'asc',
        'per_page': str(GITHUB_ISSUES_PER_PAGE),
        'page': page,
    })

    list_issues_url = f'/repos/{repo_owner}/{repo_name}/issues'
    url = f'{GITHUB_API_BASE_URL}{list_issues_url}?%s' % urllib.parse.urlencode(params)

    pages_processed = 0

    while url:
        r = requests.get(url, headers=GITHUB_API_DEFAULT_HEADERS)
        if r.status_code != 200:
            logger.error('Error %s: %s (%s) for Url: %s', r.status_code, r.content, r.reason, url)
            ingest_github_issues.apply_async(
                kwargs={
                    'project_id': project_id,
                    'repo_owner': repo_owner,
                    'repo_name': repo_name,
                    'page': page,
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

                logger.debug(
                    'Project(%s): RawIssue %s',
                    project_id,
                    issue['created_at'],
                )
                RawIssue.objects.update_or_create(
                    project_id=project_id,
                    issue_refid=issue['number'],
                    opened_at=issue['created_at'],
                    closed_at=issue['closed_at'],
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

        pages_processed += 1
        if pages_processed >= PAGES_PER_CHUNK:
            ingest_github_issues.apply_async(
                kwargs={
                    'project_id': project_id,
                    'repo_owner': repo_owner,
                    'repo_name': repo_name,
                    'page': page + pages_processed,
                }
            )
            return

    calculate_github_issue_metrics.apply_async(
        kwargs={
            'project_id': project_id,
        }
    )

    logger.info('Project(%s): Finished ingest_github_issues. (Page: %s)', project_id, page)


@shared_task
def update_github_issues(project_id, repo_owner, repo_name, start_date):
    logger.info('Project(%s): Starting update_github_issues.', project_id)
    start_date = parse(start_date)

    params = GITHUB_API_DEFAULT_PARAMS
    params.update({
        'state': 'all',
        'sort': 'updated',
        'direction': 'asc',
        'per_page': str(GITHUB_ISSUES_PER_PAGE),
        'since': datetime.datetime.combine(start_date, datetime.time.min).isoformat()
    })

    list_issues_url = f'/repos/{repo_owner}/{repo_name}/issues'
    url = f'{GITHUB_API_BASE_URL}{list_issues_url}?%s' % urllib.parse.urlencode(params)

    min_date = None

    while url:
        r = requests.get(url, headers=GITHUB_API_DEFAULT_HEADERS)
        if r.status_code != 200:
            logger.error('Error %s: %s (%s) for Url: %s', r.status_code, r.content, r.reason, url)
            update_github_issues.apply_async(
                kwargs={
                    'project_id': project_id,
                    'repo_owner': repo_owner,
                    'repo_name': repo_name,
                    'start_date': start_date,
                },
                countdown=10,
            )
            return

        issues = json.loads(r.content)

        for issue in issues:
            try:
                issue_number = issue['number']
            except TypeError as err:
                import ipdb; ipdb.set_trace()

            issue_created_at = parse(issue['created_at']) if issue['created_at'] else None
            issue_closed_at = parse(issue['closed_at']) if issue['closed_at'] else None

            try:
                labels = [label['name'] for label in issue['labels']]
            except TypeError:
                labels = []

            logger.debug(
                'Project(%s): UPDATE RawIssue %s',
                project_id,
                issue_created_at,
            )
            RawIssue.objects.update_or_create(
                project_id=project_id,
                issue_refid=issue_number,
                defaults={
                    'opened_at': issue_created_at,
                    'closed_at': issue_closed_at,
                    'labels': labels,
                }
            )

            min_date = min_date or issue_created_at
            if issue_created_at < min_date:
                min_date = issue_created_at

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
            'start_date': min_date,
        }
    )

    logger.info('Project(%s): Finished update_github_issues.', project_id)


@shared_task
def calculate_github_issue_metrics(project_id, start_date=None):
    logger.info('Project(%s): Starting calculate_github_issue_metrics.', project_id)

    start_date = parse(start_date) if start_date else datetime.date(1970, 1, 1)

    issues_opened = defaultdict(int)
    issues_closed = defaultdict(int)
    days_open = defaultdict(int)

    issues = RawIssue.objects.filter(
        project_id=project_id,
        opened_at__date__gte=start_date,
#        labels__contained_by=GITHUB_BUG_ISSUE_LABELS,  # currently we count all issues
    ).order_by('opened_at').values(
        'issue_refid',
        'opened_at',
        'closed_at',
    )

    for issue in issues:
        opened_at = issue['opened_at'].date() if issue['opened_at'] else None
        closed_at = issue['closed_at'].date() if issue['closed_at'] else None

        issues_opened[opened_at] += 1
        if closed_at:
            issues_closed[closed_at] += 1
            days_open[closed_at] += (closed_at - opened_at).days

    # list opened issues per day
    df1 = pd.DataFrame.from_dict(issues_opened, orient='index')
    df1.columns = ['opened']
    # list the number of days issues where open
    df2 = pd.DataFrame.from_dict(days_open, orient='index')
    df2.columns = ['days_open']
    # list closed issues per day
    df3 = pd.DataFrame.from_dict(issues_closed, orient='index')
    df3.columns = ['closed']

    # combine two lists and fill with 0 (where NaN would be)
    df = pd.concat([df1, df2, df3], axis=1, sort=True)
    df = df.fillna(0)

    # make index a datetime
    df.index = pd.to_datetime(df.index)

    # fill in missing dates
    idx = pd.date_range(df.iloc[0].name, df.iloc[-1].name)
    df = df.reindex(idx, fill_value=0)

    # calculate currently open issues per day
    df['sum_opened'] = df.cumsum()['opened']
    df['sum_closed'] = df.cumsum()['closed']
    df['sum_days_open'] = df.cumsum()['days_open']
    df['avg_days_open'] = df['sum_days_open'] / df['sum_closed']
    df['now_open'] = df['sum_opened'] - df['sum_closed']
    df = df.fillna(0)

    # clean up
    del df['sum_opened']
    del df['sum_closed']
    del df['days_open']
    del df['sum_days_open']

    # create a python dict
    issues = df.to_dict('index')
    del df

    for day in issues:
        logger.debug('Project(%s): Github Issue %s.', project_id, day)
        # save the metrics to db
        metric, _ = Metric.objects.get_or_create(
            project_id=project_id,
            date=day,
        )
        metric_json = metric.metrics
        if not metric_json:
            metric_json = {}
        metric_json['github_bug_issues_opened'] = issues[day]['opened']
        metric_json['github_bug_issues_closed'] = issues[day]['closed']
        metric_json['github_bug_issues_avg_days_open'] = issues[day]['avg_days_open']
        metric_json['github_bug_issues_now_open'] = issues[day]['now_open']
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
