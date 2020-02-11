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

DAYS_PER_CHUNK = 30
PAGES_PER_CHUNK = 5

GITHUB_ISSUES_PER_PAGE = 100

GITHUB_API_BASE_URL = 'https://api.github.com'
GITHUB_API_DEFAULT_HEADERS = {
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'Codefrog',
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
    """
    DEPRECATED!
    """
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
def import_github_past_issues(project_id, repo_owner, repo_name, start_date=None):
    logger.info(
        'Project(%s): Starting import_github_past_issues. (%s)',
        project_id,
        start_date,
    )

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished import_github_past_issues.', project_id)
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

    calculate_github_issue_metrics.apply_async(
        kwargs={
            'project_id': project_id,
        },
    )
    logger.info(
        'Project(%s): Finished import_github_past_issues. (%s)',
        project_id,
        start_date,
    )

    return project_id


@shared_task
def import_open_github_issues(project_id, repo_owner, repo_name):
    logger.info('Project(%s): Starting import_open_github_issues.', project_id)

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished import_open_github_issues.', project_id)
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
            import_open_github_issues.apply_async(
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
    import_github_past_issues.apply_async(
        kwargs={
            'project_id': project_id,
            'repo_owner': repo_owner,
            'repo_name': repo_name,
            'start_date': start_date,
        }
    )

    logger.info('Project(%s): Finished import_open_github_issues.', project_id)

    return project_id

@shared_task
def calculate_github_issue_metrics(project_id):
    logger.info('Project(%s): Starting calculate_github_issue_metrics.', project_id)

    issues = Issue.objects.filter(
        project_id=project_id,
    ).order_by('opened_at', 'closed_at')

    if issues.count() == 0:
        logger.info('Project(%s): No issues found. Aborting.', project_id)
        logger.info('Project(%s): Finished calculate_github_issue_metrics.', project_id)
        return

    start_date = issues.first().opened_at
    end_date = timezone.now()

    for day in date_range(start_date, end_date):
        # open issues
        open_issues = issues.filter(
            Q(opened_at__date__lte=day)
            & (Q(closed_at__isnull=True) | Q(closed_at__date__gt=day))
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

        logger.debug(
            f'{day}: '
            f'open/age_opened/closed/age_closed/age: '
            f'{count_open_issues}/{age_opened_issues}/'
            f'{count_closed_issues}/{age_closed_issues}/{age}'
        )
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
def import_git_tags(project_id):
    logger.info(
        'Project(%s): Starting import_git_tags.',
        project_id,
    )

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished import_github_releases.', project_id)
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

    logger.info('Project(%s): Finished import_git_tags.', project_id)

    return project_id


@shared_task
def import_github_releases(project_id, repo_owner, repo_name):
    logger.info(
        'Project(%s): Starting import_github_releases.',
        project_id,
    )

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished import_github_releases.', project_id)
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
        'Project(%s): Finished import_github_releases.',
        project_id,
    )


@shared_task
def update_project_data(project_id):
    logger.info('Project(%s): Starting update_project_data.', project_id)

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished update_project_data.', project_id)
        return

    project.update_data()

    logger.info('Project(%s): Finished update_project_data.', project_id)
