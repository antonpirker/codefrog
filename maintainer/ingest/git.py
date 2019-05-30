import datetime
import logging
from collections import defaultdict

from dateutil.parser import parse

from celery import shared_task
from django.utils import timezone

from core.models import Metric
from core.utils import run_shell_command
from ingest.models import RawCodeChange

logger = logging.getLogger(__name__)

@shared_task
def ingest_code_metrics(project_id, repo_dir, start_date, end_date=None):
    """

    :param project_id:
    :param repo_dir:
    :param start_date:
    :param end_date:
    :return:
    """
    logger.info('Starting ingest_code_metrics for project %s', project_id)

    start_date = start_date if start_date else datetime.date(1970, 1, 1)
    end_date = end_date if end_date else timezone.now()
    end_date = end_date + datetime.timedelta(days=1)

    # get git commits for date range
    cmd = (
        f'git log --reverse --author-date-order'
        f' --after="{start_date.strftime("%Y-%m-%d")} 00:00"'
        f' --before="{end_date.strftime("%Y-%m-%d")} 00:00"'
        f' --pretty="%ad;%H;%aN;%aE" --date=iso8601-strict'
    )
    output = run_shell_command(cmd, cwd=repo_dir)

    for line in output.split('\n'):
        if not line:
            continue

        timestamp, git_commit_hash, author_name, author_email = line.split(';')
        added, removed = get_complexity_change(repo_dir, git_commit_hash)

        file_names = list(set(list(added.keys()) + list(removed.keys())))

        try:
            for file_name in file_names:
                logger.info('Saving RawCodeChange project(%s) / %s', project_id, timestamp)
                RawCodeChange.objects.update_or_create(
                    project_id=project_id,
                    timestamp=parse(timestamp),
                    file_path=file_name,
                    author=f'{author_name} <{author_email}>',
                    complexity_added=added[file_name],
                    complexity_removed=removed[file_name],
                )
        except ValueError as err:
            logger.error('Error saving RawCodeChange: %s', err)

        # TODO: after X days (or when loop over), trigger step2!
        # if loop is not over: start another task with the rest of the time range and exit

    logger.info('Finished ingest_code_metrics for project %s', project_id)


def calculate_code_metrics(project_id, start_date, end_date=None):
    logger.info('Starting calculate_code_metrics for project %s', project_id)

    start_date = start_date if start_date else datetime.date(1970, 1, 1)
    end_date = end_date if end_date else timezone.now()
    end_date = end_date + datetime.timedelta(days=1)

    code_changes = RawCodeChange.objects.filter(
        project_id=project_id,
        timestamp__date__gte=start_date,
        timestamp__date__lte=end_date,
    ).order_by('timestamp')

    total_complexity = 0
    complexity = defaultdict(int)
    change_frequency = defaultdict(int)

    for change in code_changes:
        day = change.timestamp.date()
        # overall project complexity
        total_complexity += change.complexity_added
        total_complexity -= change.complexity_removed
        complexity[day] = total_complexity

        # overall change frequency
        change_frequency[day] += 1

    for day in complexity.keys():
        # save the metrics to db
        metric, _ = Metric.objects.get_or_create(
            project_id=project_id,
            date=day,
        )
        metric_json = metric.metrics
        if not metric_json:
            metric_json = {}
        # metric_json['number_of_commits'] = number_of_commits[day]
        metric_json['complexity'] = complexity[day]
        metric_json['change_frequency'] = change_frequency[day]
        metric.metrics = metric_json
        metric.save()


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
        if not file_name:
            continue

        # lines added
        cmd = f'git config merge.renameLimit 99999 ' \
            f'&& git diff-tree --no-commit-id -p -r {git_commit_hash} -- "{file_name}" ' \
            f'| grep -v "^+++ " | grep "^+"'
        lines_added = run_shell_command(cmd, cwd=source_dir)

        for line in lines_added.split('\n'):
            if not line:
                continue

            line = line[1:]  # skip first character
            complexity_added[file_name] += len(line) - len(line.lstrip())

        # lines removed
        cmd = f'git config merge.renameLimit 99999 ' \
            f'&& git diff-tree --no-commit-id -p -r {git_commit_hash} -- "{file_name}" ' \
            f'| grep -v "^--- " | grep "^-"'
        lines_removed = run_shell_command(cmd, cwd=source_dir)

        for line in lines_removed.split('\n'):
            if not line:
                continue

            line = line[1:]  # skip first character
            complexity_removed[file_name] += len(line) - len(line.lstrip())

    return complexity_added, complexity_removed
