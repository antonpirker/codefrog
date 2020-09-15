import datetime
import operator
import os
from collections import defaultdict

import structlog
from celery import shared_task
from dateutil.parser import parse
from django.conf import settings

from connectors.github.utils import get_access_token
from core.models import Project, Release, STATUS_UPDATING
from core.utils import run_shell_command, log, make_one
from engine.models import CodeChange

logger = structlog.get_logger(__name__)


DAYS_PER_CHUNK = 3650


@shared_task
def clone_repo(project_id, *args, **kwargs):
    """
    Clone the remote git repository to local directory.

    If the directory already exists only a `git pull` is done.

    :return: None
    """
    logger.info('Project(%s): Starting clone_repo.', project_id)
    log(project_id, 'Cloning repository', 'start')

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished (aborted) clone_repo.', project_id)
        return

    project.status = STATUS_UPDATING
    project.save()

    git_url = project.git_url

    installation_access_token = None
    if project.private:
        installation_id = project.user.profile.github_app_installation_refid
        installation_access_token = get_access_token(installation_id)

    if os.path.exists(project.repo_dir):
        logger.info('Project(%s): Repo Exists. Start pulling new changes.', project_id)
        cmd = f'git pull'
        run_shell_command(cmd, cwd=project.repo_dir)
        logger.info('Project(%s): Finished pulling new changes.', project_id)
    else:
        logger.info('Project(%s): Start cloning.', project_id)
        if installation_access_token:
            git_url = git_url.replace('https://', f'https://x-access-token:{installation_access_token}@')

        cmd = f'git clone {git_url} "{project.repo_dir}"'
        run_shell_command(cmd)
        logger.info('Project(%s): Finished cloning.', project_id)

    logger.info('Project(%s): Getting branch name.', project_id)
    cmd = f'git rev-parse --abbrev-ref HEAD'
    branch_name = run_shell_command(cmd, cwd=project.repo_dir).strip()
    project.git_branch = branch_name
    project.save()
    logger.info('Project(%s): Finished getting branch name.', project_id)

    logger.info('Project(%s): Finished clone_repo.', project_id)
    log(project_id, 'Cloning repository', 'stop')

    return project_id


@shared_task
def import_code_changes(project_id, start_date=None, *args, **kwargs):
    """
    :param project_id:
    :param start_date:
    :return:
    """
    logger.info('Project(%s): Starting import_code_changes(%s).', project_id, start_date)
    project_id = make_one(project_id)
    log(project_id, 'Importing latest code changes', 'start')

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished (aborted) import_code_changes.', project_id)
        return

    if isinstance(start_date, str):
        start_date = parse(start_date)
    start_date = start_date.date() if start_date else datetime.date(1970, 1, 1)

    with project.get_tmp_repo_dir() as tmp_dir:
        # get first commit date
        cmd = (
            f'git rev-list --max-parents=0 HEAD '
            f' --pretty="%ad" --date=iso8601-strict-local'
        )
        output = run_shell_command(cmd, cwd=tmp_dir).split('\n')[1]
        first_commit_date = parse(output).date()

        start_date = start_date if start_date >= first_commit_date else first_commit_date

        logger.info(
            f'Project(%s): Running import_code_changes starting with %s.',
            project_id,
            start_date.strftime("%Y-%m-%d"),
        )

        # get git commits for date range
        cmd = (
            f'git log --reverse --date-order'
            f' --after="{start_date.strftime("%Y-%m-%d")} 00:00"'
            f' --pretty="%ad;~;%H;~;%aN;~;%aE" --date=iso8601-strict-local'
        )

        output = run_shell_command(cmd, cwd=tmp_dir)
        code_changes = [
            operator.add([project_id, tmp_dir], line.split(';~;'))
            for line in output.split('\n') if line
        ]

        save_code_changes.chunks(code_changes, settings.CELERY_CHUNK_SIZE).apply_async()

        logger.info('Project(%s): Finished import_code_changes(%s).', project_id, start_date)
        log(project_id, 'Importing latest code changes', 'stop')

        return project_id


@shared_task
def save_code_changes(
        project_id,
        source_dir,
        timestamp,
        git_commit_hash,
        author_name,
        author_email,
        *args,
        **kwargs,
):
    logger.info(
        'Project(%s): Starting save_code_changes(%s).',
        project_id, git_commit_hash,
    )

    # get stats
    timestamp = parse(timestamp)
    added, removed = _get_complexity_change(source_dir, git_commit_hash)
    file_names = list(set(list(added.keys()) + list(removed.keys())))

    # get commit message
    cmd = f'git log --format=%B -n 1 {git_commit_hash}'
    commit_message = run_shell_command(cmd, cwd=source_dir)

    try:
        for file_name in file_names:
            logger.debug('Project(%s): CodeChange %s', project_id, timestamp)
            CodeChange.objects.update_or_create(
                project_id=project_id,
                timestamp=timestamp,
                file_path=file_name,
                author=f'{author_name} <{author_email}>',
                complexity_added=added[file_name],
                complexity_removed=removed[file_name],
                description=commit_message,
                git_commit_hash=git_commit_hash,
            )
    except ValueError as err:
        logger.error(
            'Project(%s): Error saving CodeChange %s: %s',
            project_id, git_commit_hash, err,
        )

    logger.info(
        'Project(%s): Finished save_code_changes(%s).',
        project_id, git_commit_hash,
    )


def _get_complexity_change(source_dir, git_commit_hash):
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


@shared_task
def import_tags(project_id, *args, **kwargs):
    logger.info('Project(%s): Starting import_tags.', project_id)
    project_id = make_one(project_id)
    log(project_id, 'Importing Git tags', 'start')

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished (aborted) import_tags.', project_id)
        return

    with project.get_tmp_repo_dir() as tmp_dir:
        cmd = (
            f'git tag --list '
            f'--format "%(refname:strip=2);%(taggerdate);%(committerdate)"'
        )
        output = run_shell_command(cmd, cwd=tmp_dir)
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

        logger.info('Project(%s): Finished import_tags.', project_id)
        log(project_id, 'Importing Git tags', 'stop')

        return project_id
