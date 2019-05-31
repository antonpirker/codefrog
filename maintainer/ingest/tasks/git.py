import datetime
import logging
from collections import defaultdict

from celery import shared_task
from dateutil.parser import parse

from core.models import Metric
from core.utils import run_shell_command
from ingest.models import RawCodeChange

logger = logging.getLogger(__name__)


DAYS_PER_CHUNK = 30


@shared_task
def ingest_code_metrics(project_id, repo_dir, start_date):
    """

    :param project_id:
    :param repo_dir:
    :param start_date:
    :return:
    """
    logger.info('Starting ingest_code_metrics for project %s (%s)', project_id, start_date)

    start_date = parse(start_date).date() if start_date else datetime.date(1970, 1, 1)

    # get first commit date
    cmd = (
        f'git rev-list --max-parents=0 HEAD '
        f' --pretty="%ad" --date=iso8601-strict-local'
    )
    output = run_shell_command(cmd, cwd=repo_dir).split('\n')[1]
    first_commit_date = parse(output).date()

    start_date = start_date if start_date >= first_commit_date else first_commit_date
    end_date = start_date + datetime.timedelta(days=DAYS_PER_CHUNK)
    current_date = start_date

    # get git commits for date range
    cmd = (
        f'git log --reverse --date-order'
        f' --after="{start_date.strftime("%Y-%m-%d")} 00:00"'
        f' --before="{end_date.strftime("%Y-%m-%d")} 00:00"'
        f' --pretty="%ad;%H;%aN;%aE" --date=iso8601-strict-local'
    )
    output = run_shell_command(cmd, cwd=repo_dir)
    code_changes = [line for line in output.split('\n') if line]

    for code_change in code_changes:
        timestamp, git_commit_hash, author_name, author_email = code_change.split(';')
        timestamp = parse(timestamp)
        added, removed = get_complexity_change(repo_dir, git_commit_hash)
        file_names = list(set(list(added.keys()) + list(removed.keys())))

        try:
            for file_name in file_names:
                logger.info('Project(%s): RawCodeChange %s', project_id, timestamp)
                RawCodeChange.objects.update_or_create(
                    project_id=project_id,
                    timestamp=timestamp,
                    file_path=file_name,
                    author=f'{author_name} <{author_email}>',
                    complexity_added=added[file_name],
                    complexity_removed=removed[file_name],
                )
        except ValueError as err:
            logger.error('Error saving RawCodeChange: %s', err)

        current_date = timestamp.date()

    calculate_code_metrics.apply_async(kwargs={
        'project_id': project_id,
        'start_date': start_date,
    })

    # Get last commit
    cmd = 'git log --pretty="%ad" --date-order --date=iso8601-strict-local -1'
    output = run_shell_command(cmd, cwd=repo_dir)
    last_commit_date = parse(output).date()

    # If we are not at the end, start ingesting the next chunk
    if current_date < last_commit_date:
        if start_date == current_date:
            current_date = end_date

        ingest_code_metrics.apply_async(kwargs={
            'project_id': project_id,
            'repo_dir': repo_dir,
            'start_date': current_date,
        })

    logger.info('Finished ingest_code_metrics for project %s', project_id)


@shared_task
def calculate_code_metrics(project_id, start_date):
    logger.info('Starting calculate_code_metrics for project %s', project_id)

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

    code_changes = RawCodeChange.objects.filter(
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
        logger.info('Project(%s): Code Metric %s', project_id, day)
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
