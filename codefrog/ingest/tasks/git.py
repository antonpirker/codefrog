import datetime
import logging
import os
from collections import defaultdict

from celery import shared_task

from core.models import Metric, Release, Project
from core.utils import date_range, run_shell_command
from dateutil.parser import parse
from ingest.models import CodeChange, Complexity

logger = logging.getLogger(__name__)


DAYS_PER_CHUNK = 3650


@shared_task
def calculate_code_metrics(project_id, start_date=None):
    logger.info('Project(%s): Starting calculate_code_metrics (%s).', project_id, start_date)

    start_date = parse(start_date).date() if start_date else datetime.date(1970, 1, 1)
    end_date = start_date + datetime.timedelta(days=DAYS_PER_CHUNK)

    # Get the last known complexity as starting point. (or 0)
    total_complexity = Metric.objects.filter(
        project_id=project_id,
        date__lt=start_date,
        metrics__complexity__isnull=False,
    ).order_by('date').values_list('metrics__complexity', flat=True).last() or 0

    complexity = defaultdict(int)
    change_frequency = defaultdict(int)

    logger.info(
        f'Project(%s): Running calculate_code_metrics from %s to %s.',
        project_id,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    )

    code_changes = CodeChange.objects.filter(
        project_id=project_id,
        timestamp__date__gte=start_date,
        timestamp__date__lte=end_date,
    ).order_by('timestamp')

    for change in code_changes:
        day = change.timestamp.date()

        # overall project complexity
        total_complexity += change.complexity_added
        total_complexity -= change.complexity_removed
        complexity[day] = total_complexity

        # overall change frequency
        change_frequency[day] += 1

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

    # Fill gaps in metrics (so there is one Metric object for every day
    # that has all the metrics filled out)
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

    for day in date_range(start_date, end_date):
        metric, _ = Metric.objects.get_or_create(
            project_id=project_id,
            date=day,
        )
        metric_json = metric.metrics
        if not metric_json:
            metric_json = {}

        metric_json['complexity'] = metric_json['complexity'] \
            if 'complexity' in metric_json and metric_json['complexity']\
            else old_complexity
        metric_json['change_frequency'] = metric_json['change_frequency'] \
            if 'change_frequency' in metric_json and metric_json['change_frequency'] \
            else old_change_frequency
        metric.metrics = metric_json
        metric.save()

        old_complexity = metric_json['complexity']
        old_change_frequency = metric_json['change_frequency']

    logger.info('Project(%s): Finished calculate_code_metrics.', project_id)

def get_complexity_change(source_dir, git_commit_hash):
    """

    :param source_dir:
    :param git_commit_hash:
    :return:
    """
    complexity_added = defaultdict(int)
    complexity_removed = defaultdict(int)

    # list files that where changed
    cmd = f'git diff-tree --no-commit-id --name-only -r {git_commit_hash}'
    files_changed = run_shell_command(cmd, cwd=source_dir)

    is_root_commit = not files_changed
    if is_root_commit:
        cmd = f'git diff-tree --root --no-commit-id --name-only -r {git_commit_hash}'
        files_changed = run_shell_command(cmd, cwd=source_dir)

    for file_name in files_changed.split('\n'):
        full_file_name = os.path.join(source_dir, file_name)
        if not file_name or not os.path.exists(full_file_name):
            continue

        # lines added
        # the `|| true` forces a exit code of 0,
        # because grep returns an exit code of 1 if no lines matches.
        cmd = f'git config merge.renameLimit 99999 ' \
            f'&& git diff-tree --no-commit-id -p -r {git_commit_hash} -- "{full_file_name}" ' \
            f'| grep -v "^+++ " | grep "^+" || true'
        lines_added = run_shell_command(cmd, cwd=source_dir)

        for line in lines_added.split('\n'):
            if not line:
                continue

            line = line[1:]  # skip first character
            complexity_added[file_name] += len(line) - len(line.lstrip())

        # lines removed
        # the `|| true` forces a exit code of 0,
        # because grep returns an exit code of 1 if no lines matches.
        cmd = f'git config merge.renameLimit 99999 ' \
            f'&& git diff-tree --no-commit-id -p -r {git_commit_hash} -- "{full_file_name}" ' \
            f'| grep -v "^--- " | grep "^-" || true'
        lines_removed = run_shell_command(cmd, cwd=source_dir)

        for line in lines_removed.split('\n'):
            if not line:
                continue

            line = line[1:]  # skip first character
            complexity_removed[file_name] += len(line) - len(line.lstrip())

    return complexity_added, complexity_removed





