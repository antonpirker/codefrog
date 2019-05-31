import json
import logging
import os
import urllib
from collections import defaultdict

import pandas as pd
import requests
from celery import shared_task

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
    logger.info('Starting ingest_github_issues for project %s.', project_id)

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
        issues = json.loads(r.content)

        for issue in issues:
            try:
                labels = [label['name'] for label in issue['labels']]
            except TypeError:
                labels = []

            logger.info(
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

    logger.info('Finished ingest_github_issues for project %s.', project_id)


@shared_task
def calculate_github_issue_metrics(project_id):
    logger.info('Starting calculate_github_issue_metrics for project %s.', project_id)

    issues_opened = defaultdict(int)
    issues_closed = defaultdict(int)
    days_open = defaultdict(int)

    bug_issues = RawIssue.objects.filter(
        project_id=project_id,
        labels__contained_by=GITHUB_BUG_ISSUE_LABELS,
    ).order_by('opened_at').values(
        'issue_refid',
        'opened_at',
        'closed_at',
    )

    for issue in bug_issues:
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
        logger.info('Project(%s): Github Issue %s', project_id, day)
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

    logger.info('Finished calculate_github_issue_metrics for project %s.', project_id)


@shared_task
def ingest_github_tags(project_id, repo_owner, repo_name, page=1):
    logger.info('Starting ingest_github_tags for project %s.', project_id)

    params = GITHUB_API_DEFAULT_PARAMS
    params.update({
        'per_page': str(GITHUB_ISSUES_PER_PAGE),
        'page': page,
    })

    list_tags_url = f'/repos/{repo_owner}/{repo_name}/git/refs/tags'
    url = f'{GITHUB_API_BASE_URL}{list_tags_url}?%s' % urllib.parse.urlencode(params)

    pages_processed = 0

    while url:
        r = requests.get(url, headers=GITHUB_API_DEFAULT_HEADERS)
        content = json.loads(r.content)

        for item in content:
            tag_name = item['ref'].rpartition('/')[2]
            tag_url = '%s?%s' % (item['object']['url'], urllib.parse.urlencode(params))

            r2 = requests.get(tag_url, headers=GITHUB_API_DEFAULT_HEADERS)
            tag_content = json.loads(r2.content)

            try:
                tag_date = tag_content['author']['date']
            except KeyError:
                tag_date = tag_content['tagger']['date']

            logger.info(
                'project(%s): Github Tag %s %s',
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
            ingest_github_tags.apply_async(
                kwargs={
                    'project_id': project_id,
                    'repo_owner': repo_owner,
                    'repo_name': repo_name,
                    'page': page + pages_processed,
                }
            )
            return


    logger.info('Finished ingest_github_tags for project %s.', project_id)


@shared_task
def ingest_github_releases(project_id, repo_owner, repo_name, page=1):
    logger.info('Starting ingest_github_releases for project %s.', project_id)

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
        content = json.loads(r.content)

        for item in content:
            tag_name = item['tag_name']
            tag_date = item['published_at']
            tag_url = item['html_url']

            logger.info(
                'project(%s): Github Release %s %s',
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

    logger.info('Finished ingest_github_releases for project %s.', project_id)
