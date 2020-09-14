import datetime
from collections import defaultdict

import structlog
from celery import shared_task
from dateutil.parser import parse
from django.db.models import Q, Sum
from django.utils import timezone

from core.models import Metric, Complexity
from core.utils import date_range, log, make_one
from engine.models import CodeChange, Issue, PullRequest

logger = structlog.get_logger(__name__)

DAYS_PER_CHUNK = 365 * 10


@shared_task
def calculate_code_complexity(project_id, *args, **kwargs):
    logger.info('Project(%s): Starting calculate_code_complexity.', project_id)

    Complexity.objects.filter(project_id=project_id).delete()  # TODO: maybe do this in a better way?

    # Get the newest Complexity we have
    try:
        timestamp = Complexity.objects.filter(project_id=project_id).order_by('-timestamp').first().timestamp
    except AttributeError:
        timestamp = datetime.datetime(1970, 1, 1)

    # List all code change since the newest complexity we have
    code_changes = CodeChange.objects.filter(
        project_id=project_id,
        timestamp__gte=timestamp,
    ).order_by('file_path', 'timestamp')

    complexity = defaultdict(int)
    for change in code_changes:
        # if we do not have a complexity for the file, get the last one from the database.
        if complexity[change.file_path] == 0:
            comp = Complexity.objects.filter(
                project_id=project_id,
                file_path=change.file_path,
                timestamp__lte=change.timestamp,
            ).order_by('-timestamp').first()

            if comp:
                complexity[change.file_path] = comp.complexity

        # add/subtract the complexity of the change.
        complexity[change.file_path] += change.complexity_added
        complexity[change.file_path] -= change.complexity_removed

        # save as new Complexity object.
        Complexity.objects.create(
            project_id=project_id,
            file_path=change.file_path,
            timestamp=change.timestamp,
            complexity=complexity[change.file_path],
        )

    logger.info('Project(%s): Finished calculate_code_complexity.', project_id)


@shared_task
def calculate_code_metrics(project_id, start_date=None, *args, **kwargs):
    logger.info('Project(%s): Starting calculate_code_metrics (%s).', project_id, start_date)
    project_id = make_one(project_id)
    log(project_id, 'Calculating code evolution', 'start')


    if isinstance(start_date, str):
        start_date = parse(start_date)
    start_date = start_date.date() if start_date else datetime.date(1970, 1, 1)

    # Get the last known complexity as starting point. (or 0)
    total_complexity = Metric.objects.filter(
        project_id=project_id,
        date__lt=start_date,
        metrics__complexity__isnull=False,
    ).order_by('date').values_list('metrics__complexity', flat=True).last() or 0

    complexity = defaultdict(int)
    change_frequency = defaultdict(int)

    logger.info(
        f'Project(%s): Running calculate_code_metrics starting with %s.',
        project_id,
        start_date.strftime("%Y-%m-%d"),
    )

    code_changes = CodeChange.objects.filter(
        project_id=project_id,
        timestamp__date__gte=start_date,
    ).order_by('timestamp')

    # Calculate complexity and change frequency at the end of the respective day
    for change in code_changes:
        day = change.timestamp.date()

        # overall project complexity
        total_complexity += change.complexity_added
        total_complexity -= change.complexity_removed
        complexity[day] = total_complexity

        # overall change frequency
        change_frequency[day] += 1

    # Save calculated complexity and change frequency to metrics
    for day in complexity.keys():
        logger.debug('Project(%s): Code Metric %s', project_id, day)
        # save the metrics to db
        metric, _ = Metric.objects.get_or_create(
            project_id=project_id,
            date=day,
        )
        metric_json = metric.metrics
        if not metric_json:
            metric_json = {}

        metric_json['complexity'] = complexity[day]
        metric_json['change_frequency'] = change_frequency[day]
        metric.metrics = metric_json
        metric.save()

    # Fill gaps in metrics (so there is one Metric object all the metrics set for each and every day)
    try:
        old_metric = Metric.objects.get(
            project_id=project_id,
            date=(start_date - datetime.timedelta(days=1)),
        )
        old_complexity = old_metric.metrics['complexity']
        old_change_frequency = old_metric.metrics['change_frequency']
    except (Metric.DoesNotExist, KeyError):
        old_complexity = 0
        old_change_frequency = 0

    for day in date_range(start_date, timezone.now().date()):
        metric, _ = Metric.objects.get_or_create(
            project_id=project_id,
            date=day,
        )
        metric_json = metric.metrics
        if not metric_json:
            metric_json = {}

        metric_json['complexity'] = metric_json['complexity'] \
            if 'complexity' in metric_json and metric_json['complexity'] \
            else old_complexity
        metric_json['change_frequency'] = metric_json['change_frequency'] \
            if 'change_frequency' in metric_json and metric_json['change_frequency'] \
            else old_change_frequency
        metric.metrics = metric_json
        metric.save()

        old_complexity = metric_json['complexity']
        old_change_frequency = metric_json['change_frequency']

    logger.info('Project(%s): Finished calculate_code_metrics.', project_id)
    log(project_id, 'Calculating code evolution', 'stop')

    return project_id


@shared_task
def calculate_issue_metrics(project_id, *args, **kwargs):
    logger.info('Project(%s): Starting calculate_issue_metrics.', project_id)
    project_id = make_one(project_id)
    log(project_id, 'Calculating issue metrics', 'start')

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
            age = (age_closed_issues + age_opened_issues) / (count_closed_issues + count_open_issues)
        except ZeroDivisionError:
            age = 0

        count_issues_closed_today = issues.filter(closed_at__date=day).count()

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
        metric_json['github_issues_closed'] = count_issues_closed_today
        metric_json['github_issue_age'] = age
        metric.metrics = metric_json
        metric.save()

    logger.info('Project(%s): Finished calculate_issue_metrics.', project_id)
    log(project_id, 'Calculating issue metrics', 'stop')

    return project_id


@shared_task
def calculate_pull_request_metrics(project_id, *args, **kwargs):
    logger.info('Project(%s): Starting calculate_pull_request_metrics.', project_id)
    project_id = make_one(project_id)
    log(project_id, 'Calculating pull request metrics', 'start')

    pull_requests = PullRequest.objects.filter(
        project_id=project_id,
        merged_at__isnull=False,
    ).order_by('opened_at', 'merged_at')

    if pull_requests.count() == 0:
        logger.info('Project(%s): No pull requests found. Aborting.', project_id)
        logger.info('Project(%s): Finished calculate_pull_request_metrics.', project_id)
        return

    start_date = pull_requests.first().opened_at
    end_date = timezone.now()

    for day in date_range(start_date, end_date):
        count_pull_requests_merged_today = pull_requests.filter(merged_at__date=day).count()
        cumulative_pull_requests_age = pull_requests.filter(merged_at__date=day).aggregate(Sum('age'))['age__sum']

        logger.debug(
            f'{day}: '
            f'merged/cumulative_age: '
            f'{count_pull_requests_merged_today}/'
            f'{cumulative_pull_requests_age}'
        )
        metric, _ = Metric.objects.get_or_create(
            project_id=project_id,
            date=day,
        )

        metric_json = metric.metrics
        if not metric_json:
            metric_json = {}

        metric_json['github_pull_requests_merged'] = count_pull_requests_merged_today
        metric_json['github_pull_requests_cumulative_age'] = cumulative_pull_requests_age
        metric.metrics = metric_json
        metric.save()

    logger.info('Project(%s): Finished calculate_pull_request_metrics.', project_id)
    log(project_id, 'Calculating pull request metrics', 'stop')

    return project_id
