import datetime
import logging
from dateutil.parser import parse

from celery import shared_task
from django.utils import timezone

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

        try:
            logger.info('Saving RawCodeChange project(%s) / %s', project_id, timestamp)
            RawCodeChange.objects.update_or_create(
                project_id=project_id,
                timestamp=parse(timestamp),
                file_path='TODO! This needs to be added!',
                author=f'{author_name} <{author_email}>',
                complexity_added=added,
                complexity_removed=removed,
            )
        except ValueError as err:
            logger.error('Error saving RawCodeChange: %s', err)

        # TODO: after X days (or when loop over), trigger step2!
        # if loop is not over: start another task with the rest of the time range and exit

    logger.info('Finished ingest_code_metrics for project %s', project_id)


def get_complexity_change(source_dir, git_commit_hash):
    """

    :param source_dir:
    :param git_commit_hash:
    :return:
    """
    complexity_added = 0
    complexity_removed = 0

    # lines added
    cmd = f'git config merge.renameLimit 99999 ' \
        f'&& git show {git_commit_hash} | grep -v "^+++ " | grep "^+"'
    lines_added = run_shell_command(cmd, cwd=source_dir)

    for line in lines_added.split('\n'):
        if not line:
            continue

        line = line[1:]  # skip first character
        complexity_added += len(line) - len(line.lstrip())

    # lines removed
    cmd = f'git config merge.renameLimit 99999 ' \
        f'&& git show {git_commit_hash} | grep -v "^--- " | grep "^-"'
    lines_removed = run_shell_command(cmd, cwd=source_dir)

    for line in lines_removed.split('\n'):
        if not line:
            continue

        line = line[1:]  # skip first character
        complexity_removed += len(line) - len(line.lstrip())

    return complexity_added, complexity_removed
