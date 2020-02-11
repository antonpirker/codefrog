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
def calculate_issue_metrics(project_id):
    logger.info('Project(%s): Starting calculate_issue_metrics.', project_id)

    issues = Issue.objects.filter(
        project_id=project_id,
    ).order_by('opened_at', 'closed_at')

    if issues.count() == 0:
        logger.info('Project(%s): No issues found. Aborting.', project_id)
        logger.info('Project(%s): Finished calculate_issue_metrics.', project_id)
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

    logger.info('Project(%s): Finished calculate_issue_metrics.', project_id)


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
