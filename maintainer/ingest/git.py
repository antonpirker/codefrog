from celery import shared_task
from ingest.models import RawCodeChange
from core.utils import run_shell_command


@shared_task
def ingest_code_metrics(project_id, source_dir, start_date, end_date):
    """

    :param project_id:
    :param source_dir:
    :param start_date:
    :param end_date:
    :return:
    """
    # TODO: add one day to end date
    # get git commits for date range
    cmd = 'git log --reverse --after="%S 00:00" --before="%s 00:00" ' \
          '--author-date-order --pretty="%ad;%H;%aN;%aE" --date=iso8601-strict' % (
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
    )
    output = run_shell_command(cmd, cwd=source_dir)

    for line in output.split('\n'):
        if not line:
            continue

        timestamp, git_commit_hash, author_name, author_email = line.split(';')

        added, removed = get_complexity_change(source_dir, git_commit_hash)

        RawCodeChange.objects.create(
            project_id=project_id,
            timestamp=timestamp,
            file_path='TODO! This needs to be added!',
            author=f'{author_name}<{author_email}>',
            complexity_added=added,
            complexity_removed=removed,
        )

        # TODO: after X days (or when loop over), trigger step2!
        # if loop is not over: start another task with the rest of the time range and exit


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
