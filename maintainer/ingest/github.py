import json
import logging
import os
import urllib

import requests

from ingest.models import RawIssue

logger = logging.getLogger(__name__)

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


def ingest_github_issues(project_id, repo_owner, repo_name, start_date=None):
    logger.info('Starting ingest_code_metrics for project %s', project_id)

    params = GITHUB_API_DEFAULT_PARAMS
    params.update({
        'state': 'all',
        'sort': 'created',
        'direction': 'asc',
        'per_page': '200',
    })
    if start_date:
        params.update({
            'since': start_date,
        })

    list_issues_url = f'/repos/{repo_owner}/{repo_name}/issues'
    url = f'{GITHUB_API_BASE_URL}{list_issues_url}?%s' % urllib.parse.urlencode(params)

    while url:
        r = requests.get(url, headers=GITHUB_API_DEFAULT_HEADERS)
        content = json.loads(r.content)

        for item in content:
            try:
                labels = [label['name'] for label in item['labels']]
            except TypeError:
                import ipdb; ipdb.set_trace()

            logger.info(
                'Saving RawIssue project(%s) / %s / %s',
                project_id,
                item['created_at'],
                item['number'],
            )
            RawIssue.objects.update_or_create(
                project_id=project_id,
                issue_refid=item['number'],
                opened_at=item['created_at'],
                closed_at=item['closed_at'],
                labels=labels,
            )

        links = requests.utils.parse_header_links(r.headers['Link'])
        url = None
        for link in links:
            if link['rel'] == 'next':
                url = link['url']
                break

    logger.info('Finished ingest_code_metrics for project %s', project_id)
